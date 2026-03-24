from __future__ import annotations

"""
Neo4j node labels, relationship types, and index/constraint definitions.

Graph model:
    (:Client)-[:OWNS]->(:Campaign)-[:TARGETS]->(:AudienceSegment)
    (:Campaign)-[:ACHIEVED { period }]->(:Metric)
    (:Document)-[:DESCRIBES]->(:Campaign)
    (:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Campaign)
"""

# ── Node labels ───────────────────────────────────────────────────────────────

class N:
    CLIENT           = "Client"
    CAMPAIGN         = "Campaign"
    AD_GROUP         = "AdGroup"
    AD               = "Ad"
    AUDIENCE_SEGMENT = "AudienceSegment"
    KEYWORD          = "Keyword"
    METRIC           = "Metric"
    DOCUMENT         = "Document"
    CHUNK            = "Chunk"


# ── Relationship types ────────────────────────────────────────────────────────

class R:
    OWNS             = "OWNS"           # Client → Campaign
    CONTAINS         = "CONTAINS"       # Campaign → AdGroup → Ad
    TARGETS          = "TARGETS"        # Campaign → AudienceSegment / Ad → Keyword
    ACHIEVED         = "ACHIEVED"       # Campaign → Metric  { period }
    DESCRIBES        = "DESCRIBES"      # Document → Campaign
    HAS_CHUNK        = "HAS_CHUNK"      # Document → Chunk
    MENTIONS         = "MENTIONS"       # Chunk → Campaign / AudienceSegment
    COMPETED_WITH    = "COMPETED_WITH"  # Campaign ↔ Campaign (from reports)


# ── Schema initialisation Cypher ──────────────────────────────────────────────
# Run once at startup via GraphStoreComponent.init_schema()

CONSTRAINTS: list[str] = [
    "CREATE CONSTRAINT client_id IF NOT EXISTS FOR (n:Client) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT campaign_id IF NOT EXISTS FOR (n:Campaign) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT segment_id IF NOT EXISTS FOR (n:AudienceSegment) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE",
]

INDEXES: list[str] = [
    "CREATE INDEX campaign_client IF NOT EXISTS FOR (n:Campaign) ON (n.client_id)",
    "CREATE INDEX campaign_channel IF NOT EXISTS FOR (n:Campaign) ON (n.channel)",
    "CREATE INDEX campaign_status IF NOT EXISTS FOR (n:Campaign) ON (n.status)",
    "CREATE INDEX metric_type IF NOT EXISTS FOR (n:Metric) ON (n.type)",
    "CREATE INDEX document_collection IF NOT EXISTS FOR (n:Document) ON (n.collection)",
]
