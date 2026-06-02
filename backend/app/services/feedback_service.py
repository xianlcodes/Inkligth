import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate

logger = logging.getLogger(__name__)


class FeedbackService:
    @staticmethod
    async def create_feedback(
        db: AsyncSession,
        feedback_in: FeedbackCreate,
        user_id: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Feedback:
        feedback = Feedback(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            content=feedback_in.content,
            page_url=feedback_in.page_url,
            browser_info=feedback_in.browser_info,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        logger.info(f"Feedback created: {feedback.id} by user {user_id}")
        return feedback

    @staticmethod
    async def list_feedback(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        resolved: Optional[bool] = None,
    ) -> tuple[int, list[Feedback]]:
        query = select(Feedback)
        count_query = select(func.count(Feedback.id))
        if resolved is not None:
            query = query.where(Feedback.is_resolved == resolved)
            count_query = count_query.where(Feedback.is_resolved == resolved)
        query = query.order_by(desc(Feedback.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return count_result.scalar() or 0, list(result.scalars().all())

    @staticmethod
    async def resolve_feedback(db: AsyncSession, feedback_id: str) -> Optional[Feedback]:
        result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
        feedback = result.scalar_one_or_none()
        if not feedback:
            return None
        feedback.is_resolved = True
        await db.commit()
        await db.refresh(feedback)
        return feedback
