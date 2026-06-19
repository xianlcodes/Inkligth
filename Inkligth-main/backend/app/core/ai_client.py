import logging
import time
from typing import Optional

import httpx
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
    """Check if user has a real AI engine in DB (not dummy fallback).
    Returns False when user has no engine and no global fallback is set.
    """
    try:
        async with AlibabaSessionLocal() as user_db:
            from app.services.ai_engine_service import AIEngineService
            engine = await AIEngineService.get_default_engine(user_db, user_id)
        if engine:
            return True
    except Exception:
        pass
    # No user engine — use global fallback if configured
    return bool(settings.DEFAULT_AI_KEY)


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
    return AsyncOpenAI(
        base_url=settings.DEFAULT_AI_BASE_URL,
        api_key="dummy-key",
        timeout=300.0,
        http_client=_get_http_client(),
    )


async def get_user_default_model(_db: AsyncSession, user_id: str) -> str:
    """AIEngine 在阿里云用户数据库上"""
    async with AlibabaSessionLocal() as user_db:
        engine = await AIEngineService.get_default_engine(user_db, user_id)
    if engine:
        return engine.default_model
    return settings.DEFAULT_AI_MODEL
