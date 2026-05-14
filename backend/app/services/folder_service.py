import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.folder import Folder
from app.models.literature import Literature

logger = logging.getLogger(__name__)


class FolderService:

    @staticmethod
    async def create_folder(db: AsyncSession, user_id: str, name: str) -> Folder:
        existing = await db.execute(
            select(Folder).where(Folder.user_id == user_id, Folder.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValueError("该文件夹名已存在")

        folder = Folder(user_id=user_id, name=name)
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        logger.info(f"Folder created: {folder.id}, name: {name}, user: {user_id}")
        return folder

    @staticmethod
    async def get_user_folders(db: AsyncSession, user_id: str) -> list[dict]:
        q = (
            select(
                Folder,
                func.count(Literature.id).label("literature_count"),
            )
            .outerjoin(Literature, Literature.folder_id == Folder.id)
            .where(Folder.user_id == user_id)
            .group_by(Folder.id)
            .order_by(Folder.name)
        )
        result = await db.execute(q)
        rows = result.all()
        return [
            {
                "id": row.Folder.id,
                "user_id": row.Folder.user_id,
                "name": row.Folder.name,
                "parent_id": row.Folder.parent_id,
                "literature_count": row.literature_count,
                "created_at": row.Folder.created_at,
                "updated_at": row.Folder.updated_at,
            }
            for row in rows
        ]

    @staticmethod
    async def get_folder_by_id(db: AsyncSession, folder_id: str) -> Optional[Folder]:
        result = await db.execute(select(Folder).where(Folder.id == folder_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_folder(db: AsyncSession, folder: Folder, name: str) -> Folder:
        existing = await db.execute(
            select(Folder).where(
                Folder.user_id == folder.user_id,
                Folder.name == name,
                Folder.id != folder.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该文件夹名已存在")

        folder.name = name
        await db.commit()
        await db.refresh(folder)
        logger.info(f"Folder renamed: {folder.id}, new name: {name}")
        return folder

    @staticmethod
    async def delete_folder(db: AsyncSession, folder: Folder) -> None:
        await db.execute(
            Literature.__table__.update()
            .where(Literature.folder_id == folder.id)
            .values(folder_id=None)
        )
        await db.delete(folder)
        await db.commit()
        logger.info(f"Folder deleted: {folder.id}, name: {folder.name}")
