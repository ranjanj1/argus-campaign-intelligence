from __future__ import annotations

"""
IngestService — thin layer between the router and the ingest infrastructure.

Responsibilities:
  - Enqueue ARQ ingest jobs (async file processing).
  - Query Neo4j for document listings.
  - Delegate document deletion to IngestComponent.

The ARQ pool is initialised once at app startup (see launcher.py) and stored
on FastAPI's app.state so every request can access it without DI overhead.
"""

import logging
from typing import Any, Optional

from arq.connections import ArqRedis

from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.ingest.ingest_component import IngestComponent
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)

# Collections users may ingest into (must match pgvector tables)
VALID_COLLECTIONS = {
    "campaign_performance",
    "ad_copy_library",
    "audience_segments",
    "client_strategy_briefs",
    "monthly_reports",
    "budget_allocations",
}

# 50 MB upload cap
MAX_FILE_BYTES = 50 * 1024 * 1024


class IngestService:
    """
    Stateless service — instantiated per-request (no DI singleton needed).
    All heavy singletons are passed in by the router.
    """

    def __init__(
        self,
        arq_pool: ArqRedis,
        ingest: IngestComponent,
        graph_store: GraphStoreComponent,
        settings: Settings,
    ) -> None:
        self._arq = arq_pool
        self._ingest = ingest
        self._graph = graph_store
        self._settings = settings

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(
        self,
        filename: str,
        data: bytes,
        collection: str,
        client_id: str,
        doc_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Push an ingest job onto the ARQ queue.

        Returns a dict with job_id and status "queued".
        Falls back to synchronous ingest if the ARQ pool is unavailable
        (useful in dev without a worker running).
        """
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(
                f"File too large: {len(data) / 1_048_576:.1f} MB (max 50 MB)"
            )

        if collection not in VALID_COLLECTIONS:
            raise ValueError(
                f"Unknown collection '{collection}'. "
                f"Valid options: {sorted(VALID_COLLECTIONS)}"
            )

        try:
            job = await self._arq.enqueue_job(
                "ingest_file_job",
                filename=filename,
                data=data,
                collection=collection,
                client_id=client_id,
                doc_id=doc_id,
            )
            job_id = job.job_id if job else "unknown"
            logger.info(
                "Enqueued ingest job: file=%s collection=%s client=%s job_id=%s",
                filename, collection, client_id, job_id,
            )
            return {
                "job_id": job_id,
                "status": "queued",
                "filename": filename,
                "collection": collection,
                "client_id": client_id,
            }
        except Exception as exc:
            logger.warning(
                "ARQ unavailable (%s) — falling back to inline ingest", exc
            )
            result = await self._ingest.ingest_bytes(
                data=data,
                filename=filename,
                collection=collection,
                client_id=client_id,
                doc_id=doc_id,
            )
            return {
                "job_id": result.doc_id,
                "status": "error" if result.error else "complete",
                "filename": filename,
                "collection": collection,
                "client_id": client_id,
                "doc_id": result.doc_id,
                "chunk_count": result.chunk_count,
                "entity_count": result.entity_count,
                "error": result.error or None,
            }

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_documents(
        self,
        client_id: str,
        collection: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return documents owned by client_id from Neo4j.

        Optionally filter by collection.  Returns up to `limit` results
        ordered by ingested_at descending.
        """
        if collection:
            cypher = """
            MATCH (d:Document {client_id: $client_id, collection: $collection})
            RETURN d.id AS doc_id, d.source_file AS source_file,
                   d.collection AS collection, d.ingested_at AS ingested_at
            ORDER BY d.ingested_at DESC
            LIMIT $limit
            """
            params: dict = {
                "client_id": client_id,
                "collection": collection,
                "limit": limit,
            }
        else:
            cypher = """
            MATCH (d:Document {client_id: $client_id})
            RETURN d.id AS doc_id, d.source_file AS source_file,
                   d.collection AS collection, d.ingested_at AS ingested_at
            ORDER BY d.ingested_at DESC
            LIMIT $limit
            """
            params = {"client_id": client_id, "limit": limit}

        rows = await self._graph.query(cypher, params)
        return [dict(r) for r in rows]

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(self, doc_id: str, client_id: str) -> dict[str, Any]:
        """
        Remove a document from pgvector + Neo4j.
        Raises ValueError if the document doesn't belong to client_id.
        """
        # Ownership check
        rows = await self._graph.query(
            "MATCH (d:Document {id: $id, client_id: $client_id}) RETURN d.id AS id",
            {"id": doc_id, "client_id": client_id},
        )
        if not rows:
            raise ValueError(
                f"Document '{doc_id}' not found for client '{client_id}'"
            )

        await self._ingest.delete_document(doc_id, client_id)
        return {"doc_id": doc_id, "status": "deleted"}
