import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_engine_service import AIEngineService, decrypt_api_key

logger = logging.getLogger(__name__)


async def get_user_ai_client(db: AsyncSession, user_id: str) -> AsyncOpenAI:
    engine = await AIEngineService.get_default_engine(db, user_id)
    if engine:
        try:
            api_key = decrypt_api_key(engine.api_key)
        except Exception as e:
            logger.error(f"Failed to decrypt api key for engine {engine.id}: {e}")
            api_key = ""
        logger.info(f"Using AI engine: {engine.provider}, base_url: {engine.api_base}, model: {engine.default_model}")
        return AsyncOpenAI(
            base_url=engine.api_base,
            api_key=api_key,
            timeout=60.0,
        )

    if settings.DEFAULT_AI_KEY:
        return AsyncOpenAI(
            base_url=settings.DEFAULT_AI_BASE_URL,
            api_key=settings.DEFAULT_AI_KEY,
            timeout=60.0,
        )

    logger.warning("No AI engine configured for user %s and no global fallback set", user_id)
    return AsyncOpenAI(
        base_url=settings.DEFAULT_AI_BASE_URL,
        api_key="dummy-key",
        timeout=60.0,
    )


async def get_user_default_model(db: AsyncSession, user_id: str) -> str:
    engine = await AIEngineService.get_default_engine(db, user_id)
    if engine:
        return engine.default_model
    return settings.DEFAULT_AI_MODEL
