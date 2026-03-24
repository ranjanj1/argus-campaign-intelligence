from __future__ import annotations

"""
Collections router — GET /v1/collections/stats

Returns real vector counts per collection (from pgvector) and
graph stats (from Neo4j). No auth required — stats contain no
client-specific data.
"""

import logging

from fastapi import APIRouter

from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.vector_store.vector_store_component import VectorStoreComponent
from argus.di import get_injector
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/collections", tags=["collections"])


@router.get("/stats")
async def collection_stats():
    """
    Live stats for the Collections page.

    Returns:
      collections: list of { id, vector_count }
      neo4j: { nodes, edges, entity_types, rel_types, connected }
    """
    injector = get_injector()
    vector_store: VectorStoreComponent = injector.get(VectorStoreComponent)
    graph_store: GraphStoreComponent = injector.get(GraphStoreComponent)

    # ── pgvector counts ───────────────────────────────────────────────────────
    collections = []
    try:
        async with vector_store.engine.connect() as conn:
            rows = await conn.execute(text("""
                SELECT lpc.name AS collection,
                       COUNT(lpe.id) AS vector_count
                FROM langchain_pg_collection lpc
                LEFT JOIN langchain_pg_embedding lpe
                       ON lpe.collection_id = lpc.uuid
                GROUP BY lpc.name
                ORDER BY lpc.name
            """))
            collections = [
                {"id": row.collection, "vector_count": int(row.vector_count)}
                for row in rows.fetchall()
            ]
    except Exception as exc:
        logger.warning("Failed to fetch pgvector stats: %s", exc)

    # ── Neo4j stats ───────────────────────────────────────────────────────────
    neo4j = {"nodes": 0, "edges": 0, "entity_types": 0, "rel_types": 0, "connected": False}
    try:
        results = await graph_store.query("""
            CALL {
                MATCH (n) RETURN count(n) AS nodes
            }
            CALL {
                MATCH ()-[r]->() RETURN count(r) AS edges
            }
            CALL {
                CALL db.labels() YIELD label RETURN count(label) AS entity_types
            }
            CALL {
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN count(relationshipType) AS rel_types
            }
            RETURN nodes, edges, entity_types, rel_types
        """)
        if results:
            r = results[0]
            neo4j = {
                "nodes": r.get("nodes", 0),
                "edges": r.get("edges", 0),
                "entity_types": r.get("entity_types", 0),
                "rel_types": r.get("rel_types", 0),
                "connected": True,
            }
    except Exception as exc:
        logger.warning("Failed to fetch Neo4j stats: %s", exc)

    return {"collections": collections, "neo4j": neo4j}
