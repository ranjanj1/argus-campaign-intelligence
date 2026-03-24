from __future__ import annotations

"""
IngestComponent — orchestrates the full ingest pipeline for a single file.

Pipeline per file:
  1. IngestHelper.parse()         → list[ParsedPage]
  2. Text splitting / TableChunker → list[str] chunks
  3. VectorStoreComponent.upsert() → pgvector storage + FTS index
  4. EntityExtractor.extract()     → NER per chunk
  5. GraphStoreComponent upserts   → Document + Chunk + Entity nodes

Public method:
    result = await component.ingest_file(
        path=Path("q3_report.pdf"),
        collection="monthly_reports",
        client_id="acme_corp",
        doc_id=None,          # auto-generated UUID if omitted
    )
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from injector import inject, singleton

from argus.components.embedding.embedding_component import EmbeddingComponent
from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.ingest.entity_extractor import EntityExtractor
from argus.components.ingest.ingest_helper import IngestHelper, ParsedPage
from argus.components.ingest.table_chunker import TableChunker
from argus.components.vector_store.vector_store_component import VectorStoreComponent
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)

# Characters per text chunk for narrative documents (PDF/DOCX/TXT)
_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 150

# Rows per chunk for tabular documents (CSV/XLSX)
_ROWS_PER_CHUNK = 10


@dataclass
class IngestResult:
    doc_id: str
    collection: str
    source_file: str
    chunk_count: int = 0
    entity_count: int = 0
    error: str = ""
    extra: dict = field(default_factory=dict)


@singleton
class IngestComponent:
    """
    Singleton ingest orchestrator — injected with all storage components.

    IngestHelper and TableChunker are stateless utilities instantiated
    inline (no DI required for them).
    """

    @inject
    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingComponent,
        vector_store: VectorStoreComponent,
        graph_store: GraphStoreComponent,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._helper = IngestHelper()
        self._chunker = TableChunker()
        self._extractor = EntityExtractor()

    # ── Public API ─────────────────────────────────────────────────────────

    async def ingest_file(
        self,
        path: Path,
        collection: str,
        client_id: str,
        doc_id: str | None = None,
    ) -> IngestResult:
        """
        Ingest a file from disk into pgvector + Neo4j.

        Args:
            path:        Absolute path to the file.
            collection:  Target pgvector collection (must be in settings.pgvector.tables).
            client_id:   Owner of the document (for metadata + access control).
            doc_id:      Optional document ID; auto-generated if not provided.

        Returns:
            IngestResult with chunk_count, entity_count, or error.
        """
        doc_id = doc_id or uuid.uuid4().hex
        source_file = path.name
        result = IngestResult(
            doc_id=doc_id,
            collection=collection,
            source_file=source_file,
        )

        try:
            pages = self._helper.parse(path)
            if not pages:
                result.error = "No extractable text found"
                return result

            chunks, metadatas = self._build_chunks(
                pages, doc_id, source_file, collection, client_id, path
            )
            if not chunks:
                result.error = "Chunking produced no output"
                return result

            # ── pgvector ──────────────────────────────────────────────────
            chunk_ids = [uuid.uuid4().hex for _ in chunks]
            await self._vector_store.upsert(
                collection=collection,
                texts=chunks,
                metadatas=metadatas,
                ids=chunk_ids,
            )
            result.chunk_count = len(chunks)

            # ── Neo4j: Document node ──────────────────────────────────────
            await self._graph_store.upsert_document(
                doc_id=doc_id,
                source_file=source_file,
                client_id=client_id,
                collection=collection,
                ingested_at=datetime.now(timezone.utc).isoformat(),
            )

            # ── Neo4j: Chunk nodes + Entity extraction ────────────────────
            total_entities = 0
            for chunk_id, text, meta in zip(chunk_ids, chunks, metadatas):
                await self._graph_store.upsert_chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text_preview=text[:200],
                    vector_store_id=chunk_id,
                )
                entities = self._extractor.extract(text)
                linked = await self._extractor.upsert_to_graph(
                    entities, chunk_id, self._graph_store
                )
                total_entities += linked

            result.entity_count = total_entities
            logger.info(
                "Ingest complete: doc=%s collection=%s chunks=%d entities=%d",
                doc_id, collection, result.chunk_count, result.entity_count,
            )

        except Exception as exc:
            logger.exception("Ingest failed for %s: %s", path, exc)
            result.error = str(exc)

        return result

    async def ingest_bytes(
        self,
        data: bytes,
        filename: str,
        collection: str,
        client_id: str,
        doc_id: str | None = None,
    ) -> IngestResult:
        """
        Ingest raw file bytes (used by the HTTP upload endpoint).
        """
        doc_id = doc_id or uuid.uuid4().hex
        result = IngestResult(
            doc_id=doc_id,
            collection=collection,
            source_file=filename,
        )

        try:
            pages = self._helper.parse_bytes(data, filename)
            if not pages:
                result.error = "No extractable text found"
                return result

            chunks, metadatas = self._build_chunks(
                pages, doc_id, filename, collection, client_id,
                path=None,
            )
            if not chunks:
                result.error = "Chunking produced no output"
                return result

            chunk_ids = [uuid.uuid4().hex for _ in chunks]
            await self._vector_store.upsert(
                collection=collection,
                texts=chunks,
                metadatas=metadatas,
                ids=chunk_ids,
            )
            result.chunk_count = len(chunks)

            await self._graph_store.upsert_document(
                doc_id=doc_id,
                source_file=filename,
                client_id=client_id,
                collection=collection,
                ingested_at=datetime.now(timezone.utc).isoformat(),
            )

            total_entities = 0
            for chunk_id, text, meta in zip(chunk_ids, chunks, metadatas):
                await self._graph_store.upsert_chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text_preview=text[:200],
                    vector_store_id=chunk_id,
                )
                entities = self._extractor.extract(text)
                linked = await self._extractor.upsert_to_graph(
                    entities, chunk_id, self._graph_store
                )
                total_entities += linked

            result.entity_count = total_entities

        except Exception as exc:
            logger.exception("Ingest (bytes) failed for %s: %s", filename, exc)
            result.error = str(exc)

        return result

    async def delete_document(self, doc_id: str, client_id: str) -> None:
        """
        Remove all chunks for a document from pgvector and mark it deleted in Neo4j.
        Used by the DELETE /v1/ingest/{doc_id} endpoint.
        """
        await self._vector_store.delete_by_metadata(
            {"doc_id": doc_id, "client_id": client_id}
        )
        await self._graph_store.query(
            "MATCH (d:Document {id: $id}) DETACH DELETE d",
            {"id": doc_id},
        )
        logger.info("Deleted document doc_id=%s client=%s", doc_id, client_id)

    # ── Internals ──────────────────────────────────────────────────────────

    def _build_chunks(
        self,
        pages: list[ParsedPage],
        doc_id: str,
        source_file: str,
        collection: str,
        client_id: str,
        path: Path | None,
    ) -> tuple[list[str], list[dict]]:
        """
        Route pages to the appropriate chunker and return (texts, metadatas).
        """
        suffix = Path(source_file).suffix.lower() if source_file else ""
        is_tabular = suffix in (".csv", ".xlsx", ".xls")

        texts: list[str] = []
        metadatas: list[dict] = []

        for page in pages:
            if is_tabular:
                sheet = page.extra.get("sheet", "")
                table_chunks = self._chunker.chunk_csv(
                    page.text,
                    rows_per_chunk=_ROWS_PER_CHUNK,
                    extra={"sheet": sheet} if sheet else {},
                )
                for tc in table_chunks:
                    meta = self._base_meta(
                        doc_id, source_file, collection, client_id
                    )
                    meta.update({
                        "row_start": tc.row_start,
                        "row_end": tc.row_end,
                        "sheet": sheet,
                    })
                    texts.append(tc.text)
                    metadatas.append(meta)
            else:
                for chunk_text in _split_text(page.text, _CHUNK_SIZE, _CHUNK_OVERLAP):
                    meta = self._base_meta(
                        doc_id, source_file, collection, client_id
                    )
                    meta["page"] = page.page
                    texts.append(chunk_text)
                    metadatas.append(meta)

        return texts, metadatas

    @staticmethod
    def _base_meta(
        doc_id: str, source_file: str, collection: str, client_id: str
    ) -> dict:
        return {
            "doc_id": doc_id,
            "source_file": source_file,
            "collection": collection,
            "client_id": client_id,
        }


# ── Text splitter (no LangChain dep required) ────────────────────────────────

def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Simple recursive character splitter.
    Splits on paragraphs first, then sentences, then raw characters.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " ", ""]
    for sep in separators:
        if sep and sep in text:
            parts = text.split(sep)
            chunks: list[str] = []
            current = ""
            for part in parts:
                candidate = (current + sep + part) if current else part
                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    current = part
            if current.strip():
                chunks.append(current.strip())

            # Apply overlap between consecutive chunks
            if overlap > 0 and len(chunks) > 1:
                overlapped = [chunks[0]]
                for i in range(1, len(chunks)):
                    tail = overlapped[-1][-overlap:]
                    overlapped.append(tail + " " + chunks[i])
                return overlapped
            return chunks

    # Fallback: hard split by character
    return [
        text[i: i + chunk_size]
        for i in range(0, len(text), chunk_size - overlap)
    ]
