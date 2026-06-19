import asyncio
import logging
from sqlalchemy import select
from app.db.database import async_session_factory
from app.models.literature import Literature
from app.services.search_service import SearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        sub_blocks = [s.strip() for s in block.split("\n") if s.strip()]
        if len(sub_blocks) <= 3:
            paragraphs.extend(sub_blocks)
        else:
            paragraphs.append(block)

    if len(paragraphs) <= 1:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        paragraphs = []
        current = ""
        for line in lines:
            if len(current) + len(line) > 2000 and current:
                paragraphs.append(current.strip())
                current = line
            else:
                current = current + "\n" + line if current else line
        if current.strip():
            paragraphs.append(current.strip())

    return paragraphs


async def backfill():
    async with async_session_factory() as db:
        result = await db.execute(select(Literature).where(Literature.raw_text.isnot(None)))
        literatures = result.scalars().all()
        logger.info("Found %d literatures with text", len(literatures))

        for lit in literatures:
            await SearchService.delete_chunks(db, lit.id)

            paragraphs = split_paragraphs(lit.raw_text)
            if not paragraphs:
                logger.warning("No paragraphs for literature %s", lit.id)
                continue

            para_dicts = [{"text": p, "page": None} for p in paragraphs if p.strip()]
            try:
                await SearchService.index_literature(db, lit.id, para_dicts)
                logger.info("Indexed %d chunks for: %s", len(para_dicts), lit.title[:50])
            except Exception as e:
                logger.error("Failed to index %s: %s", lit.id, e)

    logger.info("Backfill complete")


asyncio.run(backfill())