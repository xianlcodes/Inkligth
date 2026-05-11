import math
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.literature_chunk import LiteratureChunk
from app.models.literature import Literature
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class SearchService:

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    async def index_literature(
        db: AsyncSession,
        literature_id: str,
        paragraphs: list[dict],
    ):
        texts = [p["text"] for p in paragraphs if p["text"].strip()]
        if not texts:
            return

        embeddings = await embedding_service.embed_texts(texts)

        for i, (para, emb) in enumerate(zip(paragraphs, embeddings)):
            if not para["text"].strip():
                continue
            chunk = LiteratureChunk(
                literature_id=literature_id,
                chunk_index=i,
                chunk_text=para["text"],
                page_number=para.get("page"),
                embedding=emb,
            )
            db.add(chunk)

        await db.commit()
        logger.info("Indexed %d chunks for literature %s", len(texts), literature_id)

    @staticmethod
    async def search(
        db: AsyncSession,
        user_id: str,
        query: str,
        top_n: int = 10,
    ) -> list[dict]:
        query_embedding = await embedding_service.embed_text(query)

        q = (
            select(LiteratureChunk, Literature.title)
            .join(Literature, LiteratureChunk.literature_id == Literature.id)
            .where(Literature.user_id == user_id)
            .where(LiteratureChunk.embedding.isnot(None))
        )
        result = await db.execute(q)
        rows = result.all()

        scored = []
        for chunk, title in rows:
            if not chunk.embedding:
                continue
            sim = SearchService._cosine_similarity(query_embedding, chunk.embedding)
            scored.append((sim, chunk, title))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_n]

        return [
            {
                "id": chunk.id,
                "literature_id": chunk.literature_id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "page_number": chunk.page_number,
                "literature_title": title,
                "similarity": round(float(sim), 4),
            }
            for sim, chunk, title in top
        ]

    @staticmethod
    async def delete_chunks(db: AsyncSession, literature_id: str):
        q = select(LiteratureChunk).where(LiteratureChunk.literature_id == literature_id)
        result = await db.execute(q)
        chunks = result.scalars().all()
        for chunk in chunks:
            await db.delete(chunk)
        await db.commit()