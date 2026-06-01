import hashlib
import logging
import time
import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.translation_cache import TranslationCache

logger = logging.getLogger(__name__)

CACHE_CLEANUP_THRESHOLD = 50000
MEMORY_CACHE_MAX = 2000
MEMORY_CACHE_TTL = 3600

_memory_cache: dict[str, tuple[float, str]] = {}


def _compute_hash(text: str, engine_id: str) -> str:
    raw = f"{engine_id}|{text}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _memory_get(cache_key: str) -> Optional[str]:
    entry = _memory_cache.get(cache_key)
    if entry is None:
        return None
    ts, result = entry
    if time.monotonic() - ts > MEMORY_CACHE_TTL:
        del _memory_cache[cache_key]
        return None
    return result


def _memory_set(cache_key: str, result: str) -> None:
    if len(_memory_cache) >= MEMORY_CACHE_MAX:
        oldest = min(_memory_cache, key=lambda k: _memory_cache[k][0])
        del _memory_cache[oldest]
    _memory_cache[cache_key] = (time.monotonic(), result)


class TranslationCacheService:

    @staticmethod
    async def get(
        db: AsyncSession,
        text: str,
        engine_id: str,
    ) -> Optional[str]:
        text_hash = _compute_hash(text, engine_id)

        mem_result = _memory_get(text_hash)
        if mem_result is not None:
            logger.debug("Translation cache hit (memory): %s", text_hash[:8])
            return mem_result

        stmt = select(TranslationCache).where(
            TranslationCache.engine_id == engine_id,
            TranslationCache.text_hash == text_hash,
        )
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.hit_count += 1
            entry.updated_at = None
            await db.flush()
            _memory_set(text_hash, entry.translated_text)
            logger.debug("Translation cache hit (db): %s, hits=%d", text_hash[:8], entry.hit_count)
            return entry.translated_text

        return None

    @staticmethod
    async def set(
        db: AsyncSession,
        text: str,
        translated_text: str,
        engine_id: str,
    ) -> None:
        text_hash = _compute_hash(text, engine_id)
        _memory_set(text_hash, translated_text)

        stmt = insert(TranslationCache).values(
            id=str(uuid.uuid4()),
            engine_id=engine_id,
            text_hash=text_hash,
            source_text=text,
            translated_text=translated_text,
        ).on_conflict_do_nothing()

        await db.execute(stmt)
        await db.flush()

    @staticmethod
    async def invalidate_engine(db: AsyncSession, engine_id: str) -> int:
        _memory_cache.clear()
        stmt = delete(TranslationCache).where(
            TranslationCache.engine_id == engine_id,
        )
        result = await db.execute(stmt)
        deleted = result.rowcount
        if deleted:
            logger.info("Invalidated %d cache entries for engine %s", deleted, engine_id)
        return deleted

    @staticmethod
    async def cleanup_old_entries(db: AsyncSession) -> int:
        count_stmt = select(TranslationCache).limit(1).offset(CACHE_CLEANUP_THRESHOLD)
        count_result = await db.execute(count_stmt)
        if count_result.scalar_one_or_none() is None:
            return 0

        stmt = delete(TranslationCache).where(
            TranslationCache.id.in_(
                select(TranslationCache.id)
                .order_by(TranslationCache.hit_count.asc(), TranslationCache.created_at.asc())
                .limit(1000)
            )
        )
        result = await db.execute(stmt)
        deleted = result.rowcount
        if deleted:
            logger.info("Cleaned up %d low-hit cache entries", deleted)
        return deleted

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        total_stmt = select(TranslationCache)
        total_result = await db.execute(total_stmt)
        entries = total_result.scalars().all()
        if not entries:
            return {"total_entries": 0, "total_hits": 0, "avg_hits": 0}

        total_hits = sum(e.hit_count for e in entries)
        return {
            "total_entries": len(entries),
            "total_hits": total_hits,
            "avg_hits": round(total_hits / len(entries), 2),
        }