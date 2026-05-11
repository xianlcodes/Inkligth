import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.models.tag import Tag, literature_tags
from app.models.literature import Literature
from app.schemas.tag import TagCreate

logger = logging.getLogger(__name__)


class TagService:

    @staticmethod
    async def get_or_create_tag(db: AsyncSession, user_id: str, name: str) -> Tag:
        name = name.strip().lower()
        q = select(Tag).where(Tag.user_id == user_id, Tag.name == name)
        result = await db.execute(q)
        tag = result.scalar_one_or_none()
        if tag:
            return tag

        import uuid
        tag = Tag(id=str(uuid.uuid4()), user_id=user_id, name=name)
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        logger.info(f"Tag created: {tag.id}, name: {name}")
        return tag

    @staticmethod
    async def add_tag_to_literature(db: AsyncSession, user_id: str, literature_id: str, tag_name: str) -> Tag:
        literature = await db.get(Literature, literature_id)
        if not literature or literature.user_id != user_id:
            raise ValueError("文献不存在")

        tag = await TagService.get_or_create_tag(db, user_id, tag_name)

        q = select(literature_tags).where(
            literature_tags.c.literature_id == literature_id,
            literature_tags.c.tag_id == tag.id,
        )
        result = await db.execute(q)
        if not result.first():
            await db.execute(literature_tags.insert().values(literature_id=literature_id, tag_id=tag.id))
            await db.commit()
            logger.info(f"Tag '{tag_name}' added to literature {literature_id}")

        return tag

    @staticmethod
    async def remove_tag_from_literature(db: AsyncSession, user_id: str, literature_id: str, tag_id: str) -> None:
        literature = await db.get(Literature, literature_id)
        if not literature or literature.user_id != user_id:
            raise ValueError("文献不存在")

        await db.execute(
            delete(literature_tags).where(
                literature_tags.c.literature_id == literature_id,
                literature_tags.c.tag_id == tag_id,
            )
        )
        await db.commit()
        logger.info(f"Tag {tag_id} removed from literature {literature_id}")

    @staticmethod
    async def get_literature_tags(db: AsyncSession, user_id: str, literature_id: str) -> list[Tag]:
        q = (
            select(Tag)
            .join(literature_tags, Tag.id == literature_tags.c.tag_id)
            .where(literature_tags.c.literature_id == literature_id, Tag.user_id == user_id)
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_tag_cloud(db: AsyncSession, user_id: str) -> list[dict]:
        q = (
            select(Tag.name, func.count(literature_tags.c.literature_id).label("count"))
            .join(literature_tags, Tag.id == literature_tags.c.tag_id)
            .where(Tag.user_id == user_id)
            .group_by(Tag.name)
            .order_by(func.count(literature_tags.c.literature_id).desc())
        )
        result = await db.execute(q)
        return [{"name": row[0], "count": row[1]} for row in result.all()]

    @staticmethod
    async def get_literatures_by_tag(
        db: AsyncSession, user_id: str, tag_name: str, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Literature]]:
        tag_name = tag_name.strip().lower()
        count_q = (
            select(func.count())
            .select_from(Literature)
            .join(literature_tags, Literature.id == literature_tags.c.literature_id)
            .join(Tag, Tag.id == literature_tags.c.tag_id)
            .where(Literature.user_id == user_id, Tag.name == tag_name)
        )
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(Literature)
            .join(literature_tags, Literature.id == literature_tags.c.literature_id)
            .join(Tag, Tag.id == literature_tags.c.tag_id)
            .where(Literature.user_id == user_id, Tag.name == tag_name)
            .order_by(Literature.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        items = list(result.scalars().all())
        return total, items