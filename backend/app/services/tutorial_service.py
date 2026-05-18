import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.tutorial import Tutorial, TutorialVersion

logger = logging.getLogger(__name__)


class TutorialService:

    @staticmethod
    async def get_published_tutorials(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[int, list[Tutorial]]:
        base_q = select(Tutorial).where(Tutorial.is_published == True)
        count_q = select(func.count()).select_from(base_q.subquery())
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(Tutorial)
            .where(Tutorial.is_published == True)
            .order_by(desc(Tutorial.published_at), desc(Tutorial.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        return total, list(result.scalars().all())

    @staticmethod
    async def get_all_tutorials(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[Tutorial]]:
        count_q = select(func.count()).select_from(Tutorial)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(Tutorial)
            .order_by(desc(Tutorial.updated_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        return total, list(result.scalars().all())

    @staticmethod
    async def get_tutorial_by_id(db: AsyncSession, tutorial_id: str) -> Optional[Tutorial]:
        q = select(Tutorial).where(Tutorial.id == tutorial_id)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_published_tutorial_by_id(db: AsyncSession, tutorial_id: str) -> Optional[Tutorial]:
        q = select(Tutorial).where(Tutorial.id == tutorial_id, Tutorial.is_published == True)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_tutorial(db: AsyncSession, data: dict, user_id: str) -> Tutorial:
        tutorial = Tutorial(
            title=data["title"],
            content=data.get("content", ""),
            summary=data.get("summary"),
            created_by=user_id,
        )
        db.add(tutorial)
        await db.commit()
        await db.refresh(tutorial)
        logger.info("Tutorial created: %s by user %s", tutorial.id, user_id)
        return tutorial

    @staticmethod
    async def update_tutorial(
        db: AsyncSession,
        tutorial: Tutorial,
        data: dict,
        user_id: str,
        create_version: bool = True,
    ) -> Tutorial:
        if create_version and (data.get("content") is not None or data.get("title") is not None):
            await TutorialService._save_version(db, tutorial, user_id)

        was_unpublished = not tutorial.is_published
        for key, value in data.items():
            if value is not None:
                setattr(tutorial, key, value)

        if was_unpublished and tutorial.is_published:
            from datetime import datetime
            tutorial.published_at = tutorial.published_at or datetime.utcnow()

        await db.commit()
        await db.refresh(tutorial)
        logger.info("Tutorial updated: %s by user %s", tutorial.id, user_id)
        return tutorial

    @staticmethod
    async def delete_tutorial(db: AsyncSession, tutorial: Tutorial) -> None:
        await db.delete(tutorial)
        await db.commit()
        logger.info("Tutorial deleted: %s", tutorial.id)

    @staticmethod
    async def _save_version(db: AsyncSession, tutorial: Tutorial, user_id: str) -> None:
        max_version_q = (
            select(func.coalesce(func.max(TutorialVersion.version_number), 0))
            .where(TutorialVersion.tutorial_id == tutorial.id)
        )
        result = await db.execute(max_version_q)
        current_max = result.scalar() or 0
        next_version = current_max + 1

        version = TutorialVersion(
            tutorial_id=tutorial.id,
            version_number=next_version,
            title=tutorial.title,
            content=tutorial.content,
            summary=tutorial.summary,
            created_by=user_id,
        )
        db.add(version)
        logger.info("Tutorial version saved: %s v%d", tutorial.id, next_version)

    @staticmethod
    async def get_versions(
        db: AsyncSession,
        tutorial_id: str,
    ) -> list[TutorialVersion]:
        q = (
            select(TutorialVersion)
            .where(TutorialVersion.tutorial_id == tutorial_id)
            .order_by(desc(TutorialVersion.version_number))
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_version_by_id(db: AsyncSession, version_id: str) -> Optional[TutorialVersion]:
        q = select(TutorialVersion).where(TutorialVersion.id == version_id)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def restore_version(
        db: AsyncSession,
        tutorial: Tutorial,
        version: TutorialVersion,
        user_id: str,
    ) -> Tutorial:
        await TutorialService._save_version(db, tutorial, user_id)

        tutorial.title = version.title
        tutorial.content = version.content
        tutorial.summary = version.summary
        await db.commit()
        await db.refresh(tutorial)
        logger.info("Tutorial version restored: %s -> v%d by user %s", tutorial.id, version.version_number, user_id)
        return tutorial