import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_

from app.models.announcement import Announcement

logger = logging.getLogger(__name__)


class AnnouncementService:

    @staticmethod
    async def get_active_announcements(db: AsyncSession) -> list[Announcement]:
        q = (
            select(Announcement)
            .where(
                Announcement.is_published == True,
                or_(
                    Announcement.expires_at == None,
                    Announcement.expires_at > func.now(),
                ),
            )
            .order_by(
                Announcement.is_pinned.desc(),
                Announcement.published_at.desc().nulls_last(),
            )
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_public_announcements(db: AsyncSession) -> list[Announcement]:
        q = (
            select(Announcement)
            .where(
                Announcement.is_published == True,
                Announcement.scope == "site_wide",
                or_(
                    Announcement.expires_at == None,
                    Announcement.expires_at > func.now(),
                ),
            )
            .order_by(
                Announcement.is_pinned.desc(),
                Announcement.published_at.desc().nulls_last(),
            )
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_announcements(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[Announcement]]:
        count_q = select(func.count()).select_from(Announcement)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(Announcement)
            .order_by(
                Announcement.is_pinned.desc(),
                Announcement.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        items = list(result.scalars().all())
        return total, items

    @staticmethod
    async def get_announcement_by_id(db: AsyncSession, announcement_id: str) -> Optional[Announcement]:
        q = select(Announcement).where(Announcement.id == announcement_id)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_announcement(db: AsyncSession, data: dict) -> Announcement:
        announcement = Announcement(**data)
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)
        logger.info(f"Announcement created: {announcement.id}, title: {data.get('title')}")
        return announcement

    @staticmethod
    async def update_announcement(db: AsyncSession, announcement: Announcement, data: dict) -> Announcement:
        for key, value in data.items():
            if value is not None:
                setattr(announcement, key, value)
        await db.commit()
        await db.refresh(announcement)
        logger.info(f"Announcement updated: {announcement.id}")
        return announcement

    @staticmethod
    async def delete_announcement(db: AsyncSession, announcement: Announcement) -> None:
        await db.delete(announcement)
        await db.commit()
        logger.info(f"Announcement deleted: {announcement.id}")
