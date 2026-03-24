from __future__ import annotations

"""
Cypher query library.

All queries are plain strings with named parameters ($param).
Used by GraphStoreComponent and the RAG retrieval node.
"""

# ── Ingest writes ─────────────────────────────────────────────────────────────

UPSERT_CLIENT = """
MERGE (cl:Client {id: $id})
SET cl.name      = $name,
    cl.industry  = $industry,
    cl.tier       = $tier
"""

UPSERT_CAMPAIGN = """
MERGE (c:Campaign {id: $id})
SET c.name        = $name,
    c.channel     = $channel,
    c.status      = $status,
    c.start_date  = $start_date,
    c.end_date    = $end_date,
    c.client_id   = $client_id
WITH c
MERGE (cl:Client {id: $client_id})
MERGE (cl)-[:OWNS]->(c)
"""

UPSERT_SEGMENT = """
MERGE (s:AudienceSegment {id: $id})
SET s.name          = $name,
    s.age_range     = $age_range,
    s.gender        = $gender,
    s.platform      = $platform,
    s.client_id     = $client_id
WITH s
MERGE (c:Campaign {id: $campaign_id})
MERGE (c)-[:TARGETS]->(s)
"""

UPSERT_METRIC = """
MERGE (c:Campaign {id: $campaign_id})
MERGE (m:Metric {type: $type, period: $period, campaign_id: $campaign_id})
SET m.value    = $value,
    m.unit     = $unit
MERGE (c)-[:ACHIEVED {period: $period}]->(m)
"""

UPSERT_DOCUMENT = """
MERGE (d:Document {id: $id})
SET d.source_file  = $source_file,
    d.client_id    = $client_id,
    d.collection   = $collection,
    d.ingested_at  = $ingested_at
"""

LINK_DOCUMENT_TO_CAMPAIGN = """
MATCH (d:Document {id: $doc_id})
MATCH (c:Campaign {id: $campaign_id})
MERGE (d)-[:DESCRIBES]->(c)
"""

UPSERT_CHUNK = """
MERGE (ch:Chunk {id: $id})
SET ch.text_preview    = $text_preview,
    ch.vector_store_id = $vector_store_id
WITH ch
MATCH (d:Document {id: $doc_id})
MERGE (d)-[:HAS_CHUNK]->(ch)
"""

LINK_CHUNK_TO_ENTITY = """
MATCH (ch:Chunk {id: $chunk_id})
MATCH (e {id: $entity_id})
MERGE (ch)-[:MENTIONS]->(e)
"""

# ── RAG retrieval reads ───────────────────────────────────────────────────────

GET_CAMPAIGN_CONTEXT = """
MATCH (cl:Client {id: $client_id})-[:OWNS]->(c:Campaign)
OPTIONAL MATCH (c)-[:TARGETS]->(s:AudienceSegment)
OPTIONAL MATCH (c)-[:ACHIEVED]->(m:Metric)
RETURN c.id          AS campaign_id,
       c.name        AS campaign_name,
       c.channel     AS channel,
       c.status      AS status,
       c.start_date  AS start_date,
       c.end_date    AS end_date,
       collect(DISTINCT s.name)  AS segments,
       collect(DISTINCT {type: m.type, value: m.value, period: m.period}) AS metrics
ORDER BY c.name
LIMIT $limit
"""

GET_TOP_CAMPAIGNS_BY_METRIC = """
MATCH (cl:Client {id: $client_id})-[:OWNS]->(c:Campaign)
MATCH (c)-[:ACHIEVED]->(m:Metric {type: $metric_type})
RETURN c.id    AS campaign_id,
       c.name  AS campaign_name,
       m.value AS metric_value,
       m.period AS period
ORDER BY m.value DESC
LIMIT $limit
"""

GET_SEGMENTS_FOR_CAMPAIGNS = """
MATCH (cl:Client {id: $client_id})-[:OWNS]->(c:Campaign)-[:TARGETS]->(s:AudienceSegment)
RETURN s.id       AS segment_id,
       s.name     AS segment_name,
       s.platform AS platform,
       collect(DISTINCT c.name) AS campaigns
ORDER BY s.name
"""

GET_DOCUMENT_CHUNKS = """
MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(ch:Chunk)
RETURN ch.id             AS chunk_id,
       ch.text_preview   AS text_preview,
       ch.vector_store_id AS vector_store_id
"""

GET_RELATED_CAMPAIGNS = """
MATCH (c:Campaign {id: $campaign_id})-[:TARGETS]->(s:AudienceSegment)<-[:TARGETS]-(other:Campaign)
WHERE other.id <> $campaign_id
RETURN DISTINCT other.id   AS campaign_id,
                other.name AS campaign_name,
                other.channel AS channel
LIMIT $limit
"""

# ── Cleanup ───────────────────────────────────────────────────────────────────

DELETE_CLIENT_DATA = """
MATCH (cl:Client {id: $client_id})-[:OWNS]->(c:Campaign)
OPTIONAL MATCH (c)-[:ACHIEVED]->(m:Metric)
OPTIONAL MATCH (c)-[:TARGETS]->(s:AudienceSegment)
DETACH DELETE c, m, s
WITH cl
DETACH DELETE cl
"""

DELETE_DOCUMENT = """
MATCH (d:Document {id: $doc_id})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(ch:Chunk)
DETACH DELETE d, ch
"""
