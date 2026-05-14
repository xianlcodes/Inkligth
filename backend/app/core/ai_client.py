import logging
from typing import Optional

import httpx
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_engine_service import AIEngineService, decrypt_api_key

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            timeout=httpx.Timeout(300.0, connect=30.0),
        )
    return _http_client


async def get_user_ai_client(db: AsyncSession, user_id: str) -> AsyncOpenAI:
    engine = await AIEngineService.get_default_engine(db, user_id)
    if engine:
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
        logger.info(
            "Using AI engine: %s, base_url: %s (normalized from %s), model: %s",
            engine.provider, base_url, engine.api_base, engine.default_model
        )
        return AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=300.0,
            http_client=_get_http_client(),
        )

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


async def get_user_default_model(db: AsyncSession, user_id: str) -> str:
    engine = await AIEngineService.get_default_engine(db, user_id)
    if engine:
        return engine.default_model
    return settings.DEFAULT_AI_MODEL
