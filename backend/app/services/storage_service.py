import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user_storage import UserStorage
from app.models.literature import Literature

logger = logging.getLogger(__name__)

BASE_STORAGE = 200 * 1024 * 1024
MAX_STORAGE = 500 * 1024 * 1024


class StorageService:
    @staticmethod
    async def get_or_create_storage(db: AsyncSession, user_id: str) -> UserStorage:
        result = await db.execute(select(UserStorage).where(UserStorage.user_id == user_id))
        storage = result.scalar_one_or_none()
        if not storage:
            storage = UserStorage(user_id=user_id)
            db.add(storage)
            await db.commit()
            await db.refresh(storage)
        return storage

    @staticmethod
    async def get_storage(db: AsyncSession, user_id: str) -> UserStorage:
        return await StorageService.get_or_create_storage(db, user_id)

    @staticmethod
    async def add_used_space(db: AsyncSession, user_id: str, bytes_count: int) -> UserStorage:
        storage = await StorageService.get_or_create_storage(db, user_id)
        storage.used_space += bytes_count
        await db.commit()
        await db.refresh(storage)
        return storage

    @staticmethod
    async def release_used_space(db: AsyncSession, user_id: str, bytes_count: int) -> UserStorage:
        storage = await StorageService.get_or_create_storage(db, user_id)
        storage.used_space = max(0, storage.used_space - bytes_count)
        await db.commit()
        await db.refresh(storage)
        return storage

    @staticmethod
    async def add_bonus_space(db: AsyncSession, user_id: str, bonus_type: str, bytes_count: int) -> UserStorage:
        storage = await StorageService.get_or_create_storage(db, user_id)
        new_total = storage.total_space + bytes_count
        if new_total > MAX_STORAGE:
            bytes_count = MAX_STORAGE - storage.total_space
            if bytes_count <= 0:
                return storage
        storage.total_space += bytes_count
        if bonus_type == "check_in":
            storage.check_in_bonus += bytes_count
        elif bonus_type == "invitation":
            storage.invitation_bonus += bytes_count
        await db.commit()
        await db.refresh(storage)
        return storage

    @staticmethod
    async def check_space_available(db: AsyncSession, user_id: str, needed_bytes: int) -> bool:
        storage = await StorageService.get_or_create_storage(db, user_id)
        return (storage.total_space - storage.used_space) >= needed_bytes

    @staticmethod
    async def recalculate_used_space(db: AsyncSession, user_id: str) -> UserStorage:
        result = await db.execute(
            select(func.coalesce(func.sum(Literature.file_size), 0))
            .where(Literature.user_id == user_id)
        )
        total_used = result.scalar() or 0
        storage = await StorageService.get_or_create_storage(db, user_id)
        storage.used_space = total_used
        await db.commit()
        await db.refresh(storage)
        logger.info(f"Recalculated used_space for user {user_id}: {total_used} bytes")
        return storage