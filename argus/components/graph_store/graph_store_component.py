from __future__ import annotations

import logging
from typing import Any

from injector import inject, singleton
from neo4j import AsyncDriver, AsyncGraphDatabase

from argus.components.graph_store.graph_queries import (
    LINK_CHUNK_TO_ENTITY,
    LINK_DOCUMENT_TO_CAMPAIGN,
    UPSERT_CAMPAIGN,
    UPSERT_CHUNK,
    UPSERT_CLIENT,
    UPSERT_DOCUMENT,
    UPSERT_METRIC,
    UPSERT_SEGMENT,
)
from argus.components.graph_store.graph_schema import CONSTRAINTS, INDEXES
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)


@singleton
class GraphStoreComponent:
    """
    Neo4j driver singleton.

    Responsibilities:
      - Manage the async Neo4j driver lifecycle (connect / close).
      - Expose a generic query() method for ad-hoc Cypher.
      - Provide typed upsert helpers used by the ingest pipeline.
      - Run schema initialisation (constraints + indexes) at startup.
    """

    @inject
    def __init__(self, settings: Settings) -> None:
        cfg = settings.neo4j
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            cfg.uri,
            auth=(cfg.user, cfg.password),
        )
        logger.info("GraphStoreComponent initialised — uri=%s", cfg.uri)

    # ── Schema ────────────────────────────────────────────────────────────────

    async def init_schema(self) -> None:
        """Create constraints and indexes — idempotent, safe to call on every startup."""
        for statement in CONSTRAINTS + INDEXES:
            try:
                await self.query(statement)
            except Exception as exc:
                logger.warning("Schema statement skipped (%s): %s", exc, statement[:60])
        logger.info("Neo4j schema initialised")

    # ── Generic query ─────────────────────────────────────────────────────────

    async def query(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict]:
        """Run a Cypher query and return results as a list of dicts."""
        async with self._driver.session() as session:
            result = await session.run(cypher, params or {})
            return [dict(r) for r in await result.data()]

    # ── Ingest upsert helpers ─────────────────────────────────────────────────

    async def upsert_client(
        self, id: str, name: str, industry: str, tier: str = "standard"
    ) -> None:
        await self.query(UPSERT_CLIENT, {"id": id, "name": name,
                                          "industry": industry, "tier": tier})

    async def upsert_campaign(self, data: dict[str, Any]) -> None:
        """
        data keys: id, name, channel, status, start_date, end_date, client_id
        Also creates the parent Client node and OWNS relationship.
        """
        await self.query(UPSERT_CAMPAIGN, data)

    async def upsert_segment(self, data: dict[str, Any]) -> None:
        """
        data keys: id, name, age_range, gender, platform, client_id, campaign_id
        Creates TARGETS relationship between Campaign and AudienceSegment.
        """
        await self.query(UPSERT_SEGMENT, data)

    async def upsert_metric(
        self,
        campaign_id: str,
        metric_type: str,
        value: float,
        period: str,
        unit: str = "",
    ) -> None:
        """Attach a performance metric (e.g. ROAS=4.2, period=Q3-2024) to a campaign."""
        await self.query(UPSERT_METRIC, {
            "campaign_id": campaign_id,
            "type": metric_type,
            "value": value,
            "period": period,
            "unit": unit,
        })

    async def upsert_document(
        self,
        doc_id: str,
        source_file: str,
        client_id: str,
        collection: str,
        ingested_at: str,
    ) -> None:
        await self.query(UPSERT_DOCUMENT, {
            "id": doc_id,
            "source_file": source_file,
            "client_id": client_id,
            "collection": collection,
            "ingested_at": ingested_at,
        })

    async def link_document_to_campaign(
        self, doc_id: str, campaign_id: str
    ) -> None:
        await self.query(LINK_DOCUMENT_TO_CAMPAIGN,
                         {"doc_id": doc_id, "campaign_id": campaign_id})

    async def upsert_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        text_preview: str,
        vector_store_id: str,
    ) -> None:
        await self.query(UPSERT_CHUNK, {
            "id": chunk_id,
            "doc_id": doc_id,
            "text_preview": text_preview[:200],
            "vector_store_id": vector_store_id,
        })

    async def link_chunk_to_entity(
        self, chunk_id: str, entity_id: str
    ) -> None:
        await self.query(LINK_CHUNK_TO_ENTITY,
                         {"chunk_id": chunk_id, "entity_id": entity_id})

    # ── Liveness ──────────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Liveness check — verifies Neo4j connectivity."""
        await self.query("RETURN 1")
        return True

    async def close(self) -> None:
        await self._driver.close()
