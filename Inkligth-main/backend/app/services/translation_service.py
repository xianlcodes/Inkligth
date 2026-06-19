import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.translation import Translation
from app.utils.compression import compress_json, decompress_json

logger = logging.getLogger(__name__)


class TranslationService:

    @staticmethod
    def _compute_hash(content_json: str) -> str:
        return hashlib.sha256(content_json.encode("utf-8")).hexdigest()

    @staticmethod
    async def save_translation(
        db: AsyncSession,
        literature_id: str,
        user_id: str,
        paragraphs: list[dict],
        engine_version: Optional[str] = None,
        translation_style: Optional[str] = None,
    ):
        import json
        content_str = json.dumps(paragraphs, ensure_ascii=False)
        content_hash = TranslationService._compute_hash(content_str)
        compressed = compress_json(paragraphs)
        paragraph_count = str(len(paragraphs))

        translation = Translation(
            literature_id=literature_id,
            user_id=user_id,
            content_hash=content_hash,
            engine_version=engine_version,
            translation_style=translation_style,
            content=compressed,
            paragraph_count=paragraph_count,
        )
        db.add(translation)
        await db.flush()
        logger.info(
            "Translation saved: literature=%s hash=%s paragraphs=%s",
            literature_id, content_hash[:8], paragraph_count,
        )
        return translation

    @staticmethod
    async def get_translations_by_literature(
        db: AsyncSession,
        literature_id: str,
        user_id: str,
    ) -> list[Translation]:
        result = await db.execute(
            select(Translation)
            .where(
                and_(
                    Translation.literature_id == literature_id,
                    Translation.user_id == user_id,
                )
            )
            .order_by(Translation.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_latest_translation(
        db: AsyncSession,
        literature_id: str,
        user_id: str,
    ) -> Optional[Translation]:
        result = await db.execute(
            select(Translation)
            .where(
                and_(
                    Translation.literature_id == literature_id,
                    Translation.user_id == user_id,
                )
            )
            .order_by(Translation.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_translations_by_literature(
        db: AsyncSession,
        literature_id: str,
        user_id: Optional[str] = None,
    ):
        conditions = [Translation.literature_id == literature_id]
        if user_id:
            conditions.append(Translation.user_id == user_id)
        await db.execute(delete(Translation).where(and_(*conditions)))
        logger.info("Translations deleted for literature: %s", literature_id)

    @staticmethod
    async def cleanup_expired_translations(db: AsyncSession) -> int:
        cutoff = datetime.utcnow() - timedelta(days=settings.TRANSLATION_CACHE_TTL_DAYS)
        result = await db.execute(
            delete(Translation).where(Translation.created_at < cutoff)
        )
        deleted = result.rowcount
        if deleted:
            logger.info("Cleaned up %d expired translations (cutoff: %s)", deleted, cutoff.isoformat())
        return deleted

    @staticmethod
    async def delete_translations_by_engine(
        db: AsyncSession,
        user_id: str,
        engine_version: str,
    ) -> int:
        result = await db.execute(
            delete(Translation).where(
                and_(
                    Translation.user_id == user_id,
                    Translation.engine_version == engine_version,
                )
            )
        )
        deleted = result.rowcount
        if deleted:
            logger.info("Deleted %d translations for engine %s", deleted, engine_version)
        return deleted
