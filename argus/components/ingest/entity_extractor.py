from __future__ import annotations

"""
EntityExtractor — NER via spaCy → Neo4j entity upsert.

Extracts named entities from chunk text and stores them in Neo4j so the
graph can link chunks to the campaigns / orgs / products they mention.

Supported entity types (spaCy en_core_web_sm labels):
  ORG   → treated as potential campaign / brand names
  PRODUCT, WORK_OF_ART → ad/product names
  GPE, LOC             → geographic targeting
  MONEY, PERCENT       → budget / performance figures
  DATE, TIME           → temporal context

Only ORG and PRODUCT entities are upserted as Neo4j nodes; the rest are
stored as metadata on the Chunk node (future use).

GLiNER is not a hard dependency — if installed it augments spaCy results
with domain-specific labels (campaign_name, audience_segment, channel).
"""

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# spaCy labels to extract as Neo4j entity candidates
_NEO4J_LABELS = {"ORG", "PRODUCT", "WORK_OF_ART"}

# Domain-specific GLiNER labels (used only when gliner is available)
_GLINER_LABELS = [
    "campaign name",
    "audience segment",
    "marketing channel",
    "product name",
    "brand",
]


@dataclass
class ExtractedEntity:
    text: str
    label: str                          # spaCy or GLiNER label
    neo4j_id: str = ""                  # set after upsert
    extra: dict = field(default_factory=dict)


class EntityExtractor:
    """
    Stateless NER component — no DI needed; injected by IngestComponent.

    Usage:
        extractor = EntityExtractor()
        entities = extractor.extract(chunk_text)
        await extractor.upsert_to_graph(entities, chunk_id, graph_store)
    """

    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        self._nlp = self._load_spacy(spacy_model)
        self._gliner = self._load_gliner()

    # ── Public API ─────────────────────────────────────────────────────────

    def extract(self, text: str) -> list[ExtractedEntity]:
        """
        Run NER on text. Returns deduplicated entities sorted by label.
        GLiNER results are merged if available (higher precision for domain terms).
        """
        entities: dict[str, ExtractedEntity] = {}

        # spaCy pass
        doc = self._nlp(text[:100_000])   # safety cap — spaCy can OOM on huge strings
        for ent in doc.ents:
            key = f"{ent.label_}:{ent.text.strip().lower()}"
            if key not in entities:
                entities[key] = ExtractedEntity(
                    text=ent.text.strip(),
                    label=ent.label_,
                )

        # GLiNER pass (optional)
        if self._gliner is not None:
            try:
                gliner_ents = self._gliner.predict_entities(
                    text[:10_000], _GLINER_LABELS, threshold=0.5
                )
                for ent in gliner_ents:
                    key = f"{ent['label']}:{ent['text'].strip().lower()}"
                    if key not in entities:
                        entities[key] = ExtractedEntity(
                            text=ent["text"].strip(),
                            label=ent["label"],
                        )
            except Exception as exc:
                logger.debug("GLiNER extraction failed: %s", exc)

        return list(entities.values())

    async def upsert_to_graph(
        self,
        entities: list[ExtractedEntity],
        chunk_id: str,
        graph_store,           # GraphStoreComponent — avoid circular import
    ) -> int:
        """
        Upsert entity nodes in Neo4j and link them to the chunk.
        Returns the number of entities linked.

        Only entities whose label is in _NEO4J_LABELS (or domain GLiNER labels)
        are written to Neo4j.
        """
        linked = 0
        neo4j_candidates = [
            e for e in entities
            if e.label in _NEO4J_LABELS or e.label in _GLINER_LABELS
        ]
        for entity in neo4j_candidates:
            entity_id = _make_entity_id(entity.text, entity.label)
            try:
                await graph_store.query(
                    _UPSERT_ENTITY_CYPHER,
                    {
                        "id": entity_id,
                        "name": entity.text,
                        "label": entity.label,
                    },
                )
                await graph_store.link_chunk_to_entity(chunk_id, entity_id)
                entity.neo4j_id = entity_id
                linked += 1
            except Exception as exc:
                logger.warning(
                    "Failed to upsert entity '%s' (%s): %s",
                    entity.text, entity.label, exc,
                )
        return linked

    # ── Internals ──────────────────────────────────────────────────────────

    def _load_spacy(self, model: str):
        import spacy
        try:
            return spacy.load(model)
        except OSError:
            logger.warning(
                "spaCy model '%s' not found — falling back to blank English pipeline. "
                "Run: python -m spacy download %s",
                model, model,
            )
            import spacy
            return spacy.blank("en")

    def _load_gliner(self):
        try:
            from gliner import GLiNER
            model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
            logger.info("GLiNER loaded — domain-specific NER enabled")
            return model
        except ImportError:
            logger.debug("GLiNER not installed — using spaCy only")
            return None
        except Exception as exc:
            logger.warning("GLiNER failed to load: %s", exc)
            return None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_entity_id(text: str, label: str) -> str:
    """Deterministic ID: label:normalized_text"""
    return f"{label.lower()}:{text.strip().lower().replace(' ', '_')}"


_UPSERT_ENTITY_CYPHER = """
MERGE (e:Entity {id: $id})
ON CREATE SET e.name = $name, e.label = $label
ON MATCH  SET e.name = $name, e.label = $label
"""
