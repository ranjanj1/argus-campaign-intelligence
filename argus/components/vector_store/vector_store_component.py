from __future__ import annotations

import json
import logging
from typing import Any

from injector import inject, singleton
from langchain_postgres import PGVector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from argus.components.embedding.embedding_component import EmbeddingComponent
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)


@singleton
class VectorStoreComponent:
    """
    Wraps pgvector (PostgreSQL) as the vector + full-text search backend.

    PGVector stores are created lazily on first use (not in __init__) to avoid
    SQLAlchemy greenlet errors caused by sync table-creation calls at import time.

    Hybrid search combines:
      - Dense semantic search  via pgvector <=> cosine operator
      - Sparse keyword search  via PostgreSQL tsvector / plainto_tsquery
    Results are merged with Reciprocal Rank Fusion (RRF).
    """

    @inject
    def __init__(self, settings: Settings, embedder: EmbeddingComponent) -> None:
        cfg = settings.pgvector
        self._embedder = embedder
        self._tables = cfg.tables
        self._conn_str = (
            f"postgresql+asyncpg://{cfg.user}:{cfg.password}"
            f"@{cfg.host}:{cfg.port}/{cfg.database}"
        )
        # Sync connection string used by PGVector (psycopg3 binary)
        self._sync_conn_str = (
            f"postgresql+psycopg://{cfg.user}:{cfg.password}"
            f"@{cfg.host}:{cfg.port}/{cfg.database}"
        )
        self.engine: AsyncEngine = create_async_engine(self._conn_str, echo=False)
        # Stores are populated lazily via _get_store()
        self._lc_embeddings = embedder.as_langchain_embeddings()
        self._stores: dict[str, PGVector] = {}
        logger.info("VectorStoreComponent ready — collections: %s", cfg.tables)

    # ── Initialisation ────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """
        Create the pgvector extension and LangChain embedding tables.
        Called once from app startup — safe to call multiple times (idempotent).
        """
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension ready")

        # Instantiate all PGVector stores in async mode, then create their tables.
        for table in self._tables:
            store = self._get_store(table)
            try:
                await store.acreate_tables_if_not_exists()
                await store.acreate_collection()
            except Exception as exc:
                # Tables already exist on subsequent startups — safe to ignore.
                logger.debug("Collection init note for %s: %s", table, exc)
        logger.info("PGVector collections initialised")

    def _get_store(self, collection: str) -> PGVector:
        """Return (or lazily create) the PGVector store for a collection."""
        if collection not in self._stores:
            self._stores[collection] = PGVector(
                embeddings=self._lc_embeddings,
                collection_name=collection,
                connection=self._conn_str,   # asyncpg — required for async ops
                async_mode=True,
                use_jsonb=True,
            )
        return self._stores[collection]

    # ── Public API ────────────────────────────────────────────────────────────

    async def hybrid_search(
        self,
        query_text: str,
        collections: list[str],
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Run dense + sparse search across the given collections and merge with RRF.

        Args:
            query_text:   Raw query string (used for embedding and FTS).
            collections:  Collection names to search (from ClientSkill allowlist).
            filters:      JSONB metadata filter, e.g. {"client_id": "acme_corp"}.
            top_k:        Number of results after fusion.

        Returns:
            List of dicts: [{content, metadata, score, collection}]
        """
        _filters = filters or {}
        dense_results: list[tuple] = []
        sparse_results: list[tuple] = []

        for col in collections:
            if col not in self._tables:
                logger.warning("Unknown collection: %s — skipping", col)
                continue
            store = self._get_store(col)

            hits = await store.asimilarity_search_with_score(
                query_text, k=top_k, filter=_filters
            )
            for doc, score in hits:
                dense_results.append((doc.page_content, doc.metadata, score, col))

            fts_hits = await self._fts_search(col, query_text, _filters, top_k)
            sparse_results.extend(fts_hits)

        return self._reciprocal_rank_fusion(dense_results, sparse_results, top_k)

    async def upsert(
        self,
        collection: str,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str] | None = None,
    ) -> list[str]:
        """Add or replace documents in a collection. Returns stored IDs."""
        if collection not in self._tables:
            raise ValueError(f"Unknown collection: {collection}")
        store = self._get_store(collection)
        return await store.aadd_texts(texts=texts, metadatas=metadatas, ids=ids)

    async def delete_by_metadata(self, filter: dict[str, Any]) -> None:
        """Remove all chunks matching the metadata filter from every collection."""
        for name in self._tables:
            try:
                await self._get_store(name).adelete(filter=filter)
            except Exception as exc:
                logger.warning("Delete failed on collection %s: %s", name, exc)

    async def ping(self) -> bool:
        """Liveness check — verifies DB connectivity."""
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _fts_search(
        self,
        collection: str,
        query: str,
        filters: dict[str, Any],
        k: int,
    ) -> list[tuple]:
        """PostgreSQL full-text search using tsvector + plainto_tsquery."""
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                text("""
                    SELECT document, cmetadata,
                           ts_rank(
                               to_tsvector('english', document),
                               plainto_tsquery('english', :query)
                           ) AS score
                    FROM langchain_pg_embedding
                    WHERE collection_id = (
                        SELECT uuid FROM langchain_pg_collection
                        WHERE name = :collection
                    )
                    AND (:filter_empty OR cmetadata @> CAST(:filter AS jsonb))
                    AND to_tsvector('english', document)
                        @@ plainto_tsquery('english', :query)
                    ORDER BY score DESC
                    LIMIT :k
                """),
                {
                    "query": query,
                    "collection": collection,
                    "filter": json.dumps(filters),
                    "filter_empty": not bool(filters),
                    "k": k,
                },
            )
            return [
                (row.document, row.cmetadata or {}, float(row.score), collection)
                for row in rows.fetchall()
            ]

    @staticmethod
    def _reciprocal_rank_fusion(
        dense: list[tuple],
        sparse: list[tuple],
        top_k: int,
        rrf_k: int = 60,
    ) -> list[dict]:
        """Merge ranked lists with Reciprocal Rank Fusion. Score = Σ 1/(rrf_k+rank)."""
        scores: dict[str, dict] = {}

        for rank, (content, metadata, _score, collection) in enumerate(dense):
            key = content
            if key not in scores:
                scores[key] = {"content": content, "metadata": metadata,
                               "score": 0.0, "collection": collection}
            scores[key]["score"] += 1.0 / (rrf_k + rank + 1)

        for rank, (content, metadata, _score, collection) in enumerate(sparse):
            key = content
            if key not in scores:
                scores[key] = {"content": content, "metadata": metadata,
                               "score": 0.0, "collection": collection}
            scores[key]["score"] += 1.0 / (rrf_k + rank + 1)

        return sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:top_k]
