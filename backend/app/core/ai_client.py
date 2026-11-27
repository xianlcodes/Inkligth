import logging
import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_engine_service import AIEngineService, decrypt_api_key
from app.db.database import AlibabaSessionLocal

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None
_http_client_proxy: httpx.AsyncClient | None = None

_AI_CLIENT_CACHE_TTL = 300
_user_ai_cache: dict[str, tuple[float, AsyncOpenAI, str]] = {}


def _get_http_client(use_proxy: bool = False) -> httpx.AsyncClient:
    global _http_client, _http_client_proxy
    if use_proxy:
        if _http_client_proxy is None:
            proxy_url = settings.PROXY_URL
            _http_client_proxy = httpx.AsyncClient(
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                timeout=httpx.Timeout(300.0, connect=30.0),
                proxies=proxy_url,
            )
        return _http_client_proxy
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            timeout=httpx.Timeout(300.0, connect=30.0),
        )
    return _http_client


def invalidate_user_ai_cache(user_id: str) -> None:
    _user_ai_cache.pop(user_id, None)


async def has_user_ai_engine(user_id: str) -> bool:
    """严格判断用户是否配置了自己的 AI 引擎。

    注意：与旧版不同，这里不再把 DEFAULT_AI_KEY（平台免费额度）算作
    「已配置」——否则一旦平台配置了兜底 Key，所有未配引擎的用户都能
    无限量使用非 PDF 的 AI 功能（文本翻译/解析/PPT），平台免费档模型
    扛不住。平台免费额度仅限 PDF 文献翻译任务，由 QuotaService 控制。
    """
    try:
        async with AlibabaSessionLocal() as user_db:
            from app.services.ai_engine_service import AIEngineService
            engine = await AIEngineService.get_default_engine(user_db, user_id)
        return engine is not None
    except Exception as e:
        logger.warning("has_user_ai_engine check failed for %s: %s", user_id, e)
        return False


async def has_pdf_translate_access(user_id: str) -> tuple[bool, str]:
    """PDF 文献翻译的准入判断 + 通道选择。

    通道优先级（2026-11 新增用户偏好）：
    1. 用户偏好「优先免费额度」（prefer_free）且额度 > 0 且平台已配置 → platform_quota
    2. 用户自有引擎 → own_engine（无限量）
    3. 偏好免费但额度耗尽 → 自动回退自有引擎（own_engine）
    4. 无自有引擎且平台未配置/额度耗尽 → none（引导配置）

    返回 (allowed, source)：source = "own_engine" | "platform_quota" | "none"。
    """
    from app.services.platform_config_service import PlatformConfigService
    from app.services.quota_service import QuotaService

    summary = await QuotaService.get_summary(user_id)
    cfg = await PlatformConfigService.resolve()
    platform_usable = cfg["configured"] and summary["remaining"] > 0

    own_engine = await has_user_ai_engine(user_id)

    # 偏好免费额度（无论是否自有引擎），额度足够就走平台
    if summary["prefer_free"] and platform_usable:
        return True, "platform_quota"

    if own_engine:
        return True, "own_engine"

    if platform_usable:
        return True, "platform_quota"

    return False, "none"


async def get_pdf_translate_quota_summary(user_id: str) -> dict:
    """给前端展示的额度摘要：是否自有引擎 + 平台额度剩余。"""
    has_engine = await has_user_ai_engine(user_id)
    from app.services.quota_service import QuotaService
    summary = await QuotaService.get_summary(user_id)
    return {"has_ai_engine": has_engine, **summary}


async def get_cached_user_ai_client_and_model(
    _db: AsyncSession, user_id: str
) -> tuple[AsyncOpenAI, str]:
    """获取缓存的 AI 客户端和模型名（AI 引擎数据在阿里云用户数据库）"""
    cache_key = str(user_id)
    now = time.monotonic()
    if cache_key in _user_ai_cache:
        ts, client, model = _user_ai_cache[cache_key]
        if now - ts < _AI_CLIENT_CACHE_TTL:
            return client, model

    # AIEngine 在阿里云用户数据库上，使用独立的 session
    async with AlibabaSessionLocal() as user_db:
        client = await get_user_ai_client(user_db, user_id)
        model = await get_user_default_model(user_db, user_id)
    _user_ai_cache[cache_key] = (now, client, model)
    logger.debug("AI client cached for user %s, model=%s", user_id, model)
    return client, model


async def get_user_ai_client(_db: AsyncSession, user_id: str) -> AsyncOpenAI:
    """AIEngine 在阿里云用户数据库上"""
    async with AlibabaSessionLocal() as user_db:
        engine = await AIEngineService.get_default_engine(user_db, user_id)
    if engine:
        logger.info("Found AI engine %s for user %s (provider=%s, model=%s)",
                     engine.id, user_id, engine.provider, engine.default_model)
        try:
            api_key = decrypt_api_key(engine.api_key)
        except Exception as e:
            logger.error(f"Failed to decrypt api key for engine {engine.id}: {e}")
            engine = None

    if engine:
        from app.core.ai_providers.provider_registry import AIProviderRegistry
        registry = AIProviderRegistry()
        adapter = registry.get_or_default(engine.provider)
        base_url = adapter.get_openai_base_url(engine.api_base)
        use_proxy = engine.proxy_enabled and bool(settings.PROXY_URL)
        logger.debug(
            "Using AI engine: %s, base_url: %s, model: %s, proxy=%s",
            engine.provider, base_url, engine.default_model, use_proxy
        )
        return AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=300.0,
            http_client=_get_http_client(use_proxy=use_proxy),
        )

    logger.warning("No AI engine found for user %s — trying global fallback", user_id)
    if settings.DEFAULT_AI_KEY:
        return AsyncOpenAI(
            base_url=settings.DEFAULT_AI_BASE_URL,
            api_key=settings.DEFAULT_AI_KEY,
            timeout=300.0,
            http_client=_get_http_client(),
        )

    logger.warning("No AI engine configured for user %s and no global fallback set", user_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="请先配置 AI 引擎后再使用此功能",
    )


async def get_user_default_model(_db: AsyncSession, user_id: str) -> str:
    """AIEngine 在阿里云用户数据库上"""
    async with AlibabaSessionLocal() as user_db:
        engine = await AIEngineService.get_default_engine(user_db, user_id)
    if engine:
        return engine.default_model
    return settings.PLATFORM_FALLBACK_MODEL


# ============================================================
# 新增：返回原始凭据，供 pdf2zh 每次重建客户端使用
# ============================================================
async def get_user_ai_credentials(
    user_id: str, source: str | None = None
) -> tuple[str, str, str]:
    """返回 (api_key, base_url, model)。

    pdf2zh 会在子线程中通过新的事件循环调用翻译，无法复用主循环创建的
    AsyncOpenAI 客户端（httpx 连接池绑定到创建时的事件循环，跨循环复用会挂起）。
    因此这里返回原始凭据，由 Pdf2ZhTranslatorAdapter 每次翻译时新建客户端。

    通道选择（source 参数，由任务创建路由锁定后传入）：
    - "platform_quota"：直接走平台免费额度（扣减已在路由完成，此处不再校验
      remaining——否则额度刚好用尽的最后一个任务会被错误地回退到自有 Key）；
    - "own_engine" 或 None：用户自有引擎（模型不限），无引擎时回退平台额度
      （模型/Key/地址由管理员在后台「系统配置」的 platform_* 配置项管理，
      运行时生效；模型锁定免费档，不会消耗平台账户余额）。
    """
    from app.core.ai_providers.provider_registry import AIProviderRegistry
    from app.services.platform_config_service import PlatformConfigService

    # 任务创建时已锁定的通道：platform_quota → 直接走平台凭据
    # （不能重新判定——扣减后 remaining 可能已为 0，重判会错误回退到自有 Key）
    if source == "platform_quota":
        cfg = await PlatformConfigService.resolve()
        if not cfg["configured"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="平台免费额度未配置，请联系管理员或在「AI 设置」中配置自己的 Key",
            )
        logger.info(
            "get_user_ai_credentials: user=%s source=platform_quota(locked) model=%s",
            user_id, cfg["model"],
        )
        return cfg["key"], cfg["base_url"], cfg["model"]

    async with AlibabaSessionLocal() as user_db:
        engine = await AIEngineService.get_default_engine(user_db, user_id)

    if engine:
        try:
            api_key = decrypt_api_key(engine.api_key)
        except Exception as e:
            logger.error("Failed to decrypt api key for engine %s: %s", engine.id, e)
            engine = None

    if engine:
        registry = AIProviderRegistry()
        adapter = registry.get_or_default(engine.provider)
        base_url = adapter.get_openai_base_url(engine.api_base)
        logger.info(
            "get_user_ai_credentials: user=%s provider=%s model=%s base_url=%s",
            user_id, engine.provider, engine.default_model, base_url,
        )
        return api_key, base_url, engine.default_model

    # 平台免费额度兜底：配置由管理员后台管理；key 只在服务端使用，绝不下发前端、绝不写日志
    cfg = await PlatformConfigService.resolve()
    if not cfg["configured"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先配置 AI 引擎后再使用此功能",
        )

    from app.services.quota_service import QuotaService
    remaining = await QuotaService.remaining(user_id)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "免费体验额度已用完（每用户 1 篇文献）。"
                "在「AI 设置」中配置自己的 API Key 即可无限使用"
            ),
        )

    logger.info(
        "get_user_ai_credentials: user=%s source=platform_quota model=%s",
        user_id, cfg["model"],
    )
    return cfg["key"], cfg["base_url"], cfg["model"]