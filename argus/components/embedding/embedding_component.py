from __future__ import annotations

import asyncio
from typing import List

from injector import inject, singleton
from langchain_core.embeddings import Embeddings

from argus.settings.settings import Settings


class _SentenceTransformerEmbeddings(Embeddings):
    """
    Thin LangChain Embeddings adapter around a SentenceTransformer model.

    langchain_postgres.PGVector requires an object implementing:
      embed_documents(texts) -> list[list[float]]
      embed_query(text)      -> list[float]
      aembed_documents(...)  -> async versions
      aembed_query(...)      -> async versions
    """

    def __init__(self, model) -> None:
        self._model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._model.encode(texts, normalize_embeddings=True).tolist()
        )

    async def aembed_query(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._model.encode(text, normalize_embeddings=True).tolist()
        )


@singleton
class EmbeddingComponent:
    """
    Embedding provider singleton — nomic-embed-text-v1.5 (768-dim) by default.

    Runs sentence-transformers locally (no API cost).
    The `.model` property exposes the raw SentenceTransformer for LangChain integrations
    (e.g. VectorStoreComponent passes it directly to PGVector).

    Public interface:
      await embedder.embed(text)          → list[float]   (single text)
      await embedder.embed_batch(texts)   → list[list[float]]  (batch)
    """

    @inject
    def __init__(self, settings: Settings) -> None:
        self._cfg = settings.embedding
        self._model = self._load_model()

    def _load_model(self):
        from sentence_transformers import SentenceTransformer
        # trust_remote_code required for nomic-embed-text-v1.5
        return SentenceTransformer(
            self._cfg.model_name,
            trust_remote_code=True,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def embed(self, text: str) -> List[float]:
        """Embed a single text string. Runs in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None, lambda: self._model.encode(text, normalize_embeddings=True).tolist()
        )
        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts in one batched call."""
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True).tolist(),
        )
        return vectors

    @property
    def model(self):
        """Raw SentenceTransformer — for direct encode() calls."""
        return self._model

    def as_langchain_embeddings(self) -> Embeddings:
        """LangChain Embeddings adapter — pass to PGVector and other LC integrations."""
        return _SentenceTransformerEmbeddings(self._model)

    @property
    def dimensions(self) -> int:
        return self._cfg.dimensions

    @property
    def model_name(self) -> str:
        return self._cfg.model_name
