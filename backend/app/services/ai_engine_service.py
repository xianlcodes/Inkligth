import logging
import uuid
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.ai_engine import AIEngine
from app.schemas.ai_engine import AIEngineCreate, AIEngineUpdate, AIEngineTestResult
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    import base64
    import hashlib

    secret = getattr(settings, "AI_KEY_SECRET", None) or settings.SECRET_KEY
    key = secret.encode("utf-8")
    digest = hashlib.sha256(key).digest()
    url_safe_key = base64.urlsafe_b64encode(digest)
    return Fernet(url_safe_key)


def encrypt_api_key(plain_key: str) -> str:
    return _get_fernet().encrypt(plain_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    return _get_fernet().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")


def mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


class AIEngineService:
    @staticmethod
    async def create_engine(db: AsyncSession, user_id: str, data: AIEngineCreate) -> AIEngine:
        engine = AIEngine(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=data.provider,
            api_base=data.api_base,
            api_key=encrypt_api_key(data.api_key),
            default_model=data.default_model,
            fallback_models=data.fallback_models,
            is_default=data.is_default,
        )
        db.add(engine)
        await db.commit()
        await db.refresh(engine)

        if data.is_default:
            await AIEngineService.set_default_engine(db, user_id, engine.id)
            await db.refresh(engine)

        return engine

    @staticmethod
    async def get_engines_by_user(db: AsyncSession, user_id: str) -> list[AIEngine]:
        result = await db.execute(
            select(AIEngine).where(AIEngine.user_id == user_id).order_by(AIEngine.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_engine_by_id(db: AsyncSession, engine_id: str, user_id: str) -> Optional[AIEngine]:
        result = await db.execute(
            select(AIEngine).where(AIEngine.id == engine_id, AIEngine.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_engine(
        db: AsyncSession, engine: AIEngine, data: AIEngineUpdate
    ) -> AIEngine:
        if data.provider is not None:
            engine.provider = data.provider
        if data.api_base is not None:
            engine.api_base = data.api_base
        if data.api_key:
            engine.api_key = encrypt_api_key(data.api_key)
        if data.default_model is not None:
            engine.default_model = data.default_model
        if data.fallback_models is not None:
            engine.fallback_models = data.fallback_models
        if data.is_default is not None:
            engine.is_default = data.is_default

        await db.commit()
        await db.refresh(engine)

        if data.is_default:
            await AIEngineService.set_default_engine(db, engine.user_id, engine.id)
            await db.refresh(engine)

        return engine

    @staticmethod
    async def delete_engine(db: AsyncSession, engine: AIEngine) -> None:
        await db.delete(engine)
        await db.commit()

    @staticmethod
    async def set_default_engine(db: AsyncSession, user_id: str, engine_id: str) -> None:
        """批量更新：将其他引擎设为非默认，目标引擎设为默认"""
        # 1. 先取消该用户所有引擎的默认状态
        await db.execute(
            update(AIEngine)
            .where(AIEngine.user_id == user_id)
            .values(is_default=False)
        )
        # 2. 将目标引擎设为默认
        await db.execute(
            update(AIEngine)
            .where(AIEngine.id == engine_id, AIEngine.user_id == user_id)
            .values(is_default=True)
        )
        await db.commit()

    @staticmethod
    async def get_default_engine(db: AsyncSession, user_id: str) -> Optional[AIEngine]:
        """获取默认引擎，若无默认则取第一个（按创建时间升序）"""
        result = await db.execute(
            select(AIEngine)
            .where(AIEngine.user_id == user_id, AIEngine.is_default == True)
        )
        engine = result.scalar_one_or_none()
        if engine:
            return engine
        # 降级：取用户最早创建的引擎
        result = await db.execute(
            select(AIEngine)
            .where(AIEngine.user_id == user_id)
            .order_by(AIEngine.created_at.asc())
        )
        return result.scalars().first()

    @staticmethod
    async def test_engine_connection(engine: AIEngine) -> AIEngineTestResult:
        """测试引擎连接，通过 AIProviderRegistry 自动适配不同供应商"""
        from app.core.ai_providers.provider_registry import AIProviderRegistry

        decrypted_key = decrypt_api_key(engine.api_key)
        registry = AIProviderRegistry()
        adapter = registry.get_or_default(engine.provider)

        return await adapter.test_connection(
            api_base=engine.api_base,
            api_key=decrypted_key,
            model=engine.default_model,
        )