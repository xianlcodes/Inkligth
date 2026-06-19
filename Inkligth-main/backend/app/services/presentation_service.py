from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.presentation import Presentation
from app.schemas.presentation import PresentationCreate, SlideData
from typing import List, Optional


class PresentationService:

    @staticmethod
    async def create_presentation(
        db: AsyncSession,
        user_id: str,
        data: PresentationCreate,
    ) -> Presentation:
        slides_json = [s.model_dump() for s in data.slides]
        slide_count = f"{len(data.slides)} 张幻灯片"

        presentation = Presentation(
            user_id=user_id,
            literature_id=data.literature_id,
            literature_title=data.literature_title,
            slides=slides_json,
            slide_count=slide_count,
        )
        db.add(presentation)
        await db.commit()
        await db.refresh(presentation)
        return presentation

    @staticmethod
    async def get_presentations(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        count_query = select(func.count()).select_from(Presentation).where(
            Presentation.user_id == user_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(Presentation)
            .where(Presentation.user_id == user_id)
            .order_by(Presentation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        items = result.scalars().all()

        return {"total": total, "items": list(items)}

    @staticmethod
    async def get_presentation(
        db: AsyncSession,
        presentation_id: str,
        user_id: str,
    ) -> Optional[Presentation]:
        query = select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_presentation(
        db: AsyncSession,
        presentation_id: str,
        user_id: str,
    ) -> bool:
        query = delete(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user_id,
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_by_literature(
        db: AsyncSession,
        literature_id: str,
        user_id: str,
    ) -> Optional[Presentation]:
        query = (
            select(Presentation)
            .where(
                Presentation.literature_id == literature_id,
                Presentation.user_id == user_id,
            )
            .order_by(Presentation.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()