import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ai_analysis import AIAnalysis

logger = logging.getLogger(__name__)


class AnalysisService:

    @staticmethod
    async def get_analysis_by_literature(
        db: AsyncSession, user_id: str, literature_id: str
    ) -> Optional[AIAnalysis]:
        q = select(AIAnalysis).where(
            AIAnalysis.user_id == user_id,
            AIAnalysis.literature_id == literature_id,
        )
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_or_update_analysis(
        db: AsyncSession,
        user_id: str,
        literature_id: str,
        summary: dict,
        innovations: list[str],
        methods: str,
    ) -> AIAnalysis:
        existing = await AnalysisService.get_analysis_by_literature(db, user_id, literature_id)
        if existing:
            existing.summary = summary
            existing.innovations = innovations
            existing.methods = methods
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Analysis updated: {existing.id}, literature: {literature_id}")
            return existing

        analysis = AIAnalysis(
            user_id=user_id,
            literature_id=literature_id,
            summary=summary,
            innovations=innovations,
            methods=methods,
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        logger.info(f"Analysis created: {analysis.id}, literature: {literature_id}")
        return analysis