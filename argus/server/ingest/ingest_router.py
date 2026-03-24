from __future__ import annotations

"""
Ingest router — file upload, listing, and deletion endpoints.

Endpoints:
  POST   /v1/ingest/file         Upload a file → ARQ job
  GET    /v1/ingest/list         List ingested documents
  DELETE /v1/ingest/{doc_id}     Remove a document

All endpoints require a valid JWT (or auth disabled in develop profile).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.ingest.ingest_component import IngestComponent
from argus.di import get_injector, get_settings
from argus.server.ingest.ingest_service import VALID_COLLECTIONS, IngestService
from argus.server.utils.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])


# ── Dependency: build IngestService per request ───────────────────────────────

def _get_service(request: Request) -> IngestService:
    injector = get_injector()
    return IngestService(
        arq_pool=request.app.state.arq_pool,
        ingest=injector.get(IngestComponent),
        graph_store=injector.get(GraphStoreComponent),
        settings=get_settings(),
    )


# ── POST /v1/ingest/file ──────────────────────────────────────────────────────

@router.post("/file", status_code=status.HTTP_202_ACCEPTED)
async def ingest_file(
    file: UploadFile = File(..., description="File to ingest (PDF, DOCX, CSV, XLSX, TXT)"),
    collection: str = Form(
        ...,
        description=f"Target collection. One of: {sorted(VALID_COLLECTIONS)}",
    ),
    client_id: Optional[str] = Form(
        None,
        description="Override client_id (admin only). Defaults to JWT claim.",
    ),
    identity: dict = Depends(require_auth),
    service: IngestService = Depends(_get_service),
):
    """
    Upload a file for async ingestion.

    The file is read into memory and pushed onto the ARQ queue.
    The worker processes it in the background: parse → chunk → embed → store.

    Returns a job_id you can use to track status (future: GET /v1/ingest/job/{id}).
    """
    # client_id: admins (all_campaigns skill) may override; everyone else uses JWT
    from argus.utils.skills import ClientSkill
    effective_client = client_id or identity["client_id"]
    if (
        client_id
        and client_id != identity["client_id"]
        and identity["skill"] != ClientSkill.ALL_CAMPAIGNS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin skill can ingest on behalf of another client.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = await service.enqueue(
            filename=file.filename or "upload",
            data=data,
            collection=collection,
            client_id=effective_client,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return result


# ── GET /v1/ingest/list ───────────────────────────────────────────────────────

@router.get("/list")
async def list_documents(
    collection: Optional[str] = None,
    limit: int = 100,
    identity: dict = Depends(require_auth),
    service: IngestService = Depends(_get_service),
):
    """
    List ingested documents for the authenticated client.

    Optionally filter by `collection`. Results are ordered by ingested_at DESC.
    """
    if collection and collection not in VALID_COLLECTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown collection '{collection}'.",
        )

    limit = max(1, min(limit, 500))   # clamp to [1, 500]

    docs = await service.list_documents(
        client_id=identity["client_id"],
        collection=collection,
        limit=limit,
    )
    return {"client_id": identity["client_id"], "count": len(docs), "documents": docs}


# ── DELETE /v1/ingest/{doc_id} ────────────────────────────────────────────────

@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: str,
    identity: dict = Depends(require_auth),
    service: IngestService = Depends(_get_service),
):
    """
    Delete a document and all its chunks from pgvector and Neo4j.

    Only the owning client (or an admin) may delete a document.
    """
    try:
        result = await service.delete(doc_id=doc_id, client_id=identity["client_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return result
