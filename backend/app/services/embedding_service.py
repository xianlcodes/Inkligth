import logging
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _load_model(self):
        if self._model is None:
            logger.info("Loading local embedding model from %s", settings.EMBEDDING_MODEL_PATH)
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH)
        return self._model

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def embed_text(self, text: str) -> List[float]:
        results = await self.embed_texts([text])
        return results[0]


embedding_service = EmbeddingService()