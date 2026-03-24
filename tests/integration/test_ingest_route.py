"""
Integration tests for the ingest router.

These tests use FastAPI's TestClient with all external I/O mocked:
  - IngestService.enqueue  → stubbed
  - IngestService.list_documents → stubbed
  - IngestService.delete   → stubbed
  - ARQ pool               → set to None on app.state (triggers inline fallback)

No real database or Redis required.
"""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from argus.main import app


@pytest.fixture(autouse=True)
def _patch_arq(monkeypatch):
    """Ensure app.state.arq_pool exists (None = inline ingest fallback)."""
    app.state.arq_pool = None


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── POST /v1/ingest/file ──────────────────────────────────────────────────────

class TestIngestFile:
    def test_upload_csv_returns_202(self, client):
        mock_result = {
            "job_id": "abc123",
            "status": "queued",
            "filename": "data.csv",
            "collection": "campaign_performance",
            "client_id": "internal",
        }
        with patch(
            "argus.server.ingest.ingest_service.IngestService.enqueue",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = client.post(
                "/v1/ingest/file",
                files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
                data={"collection": "campaign_performance"},
            )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "queued"
        assert body["job_id"] == "abc123"

    def test_empty_file_returns_400(self, client):
        resp = client.post(
            "/v1/ingest/file",
            files={"file": ("empty.csv", b"", "text/csv")},
            data={"collection": "campaign_performance"},
        )
        assert resp.status_code == 400

    def test_invalid_collection_returns_422(self, client):
        with patch(
            "argus.server.ingest.ingest_service.IngestService.enqueue",
            new_callable=AsyncMock,
            side_effect=ValueError("Unknown collection"),
        ):
            resp = client.post(
                "/v1/ingest/file",
                files={"file": ("data.csv", b"a,b\n1,2\n", "text/csv")},
                data={"collection": "nonexistent"},
            )
        assert resp.status_code == 422

    def test_missing_collection_field_returns_422(self, client):
        resp = client.post(
            "/v1/ingest/file",
            files={"file": ("data.csv", b"a,b\n1,2\n", "text/csv")},
            # no collection form field
        )
        assert resp.status_code == 422


# ── GET /v1/ingest/list ───────────────────────────────────────────────────────

class TestListDocuments:
    def test_list_returns_documents(self, client):
        docs = [
            {
                "doc_id": "d1",
                "source_file": "q3.pdf",
                "collection": "monthly_reports",
                "ingested_at": "2024-10-01T00:00:00+00:00",
            }
        ]
        with patch(
            "argus.server.ingest.ingest_service.IngestService.list_documents",
            new_callable=AsyncMock,
            return_value=docs,
        ):
            resp = client.get("/v1/ingest/list")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["documents"][0]["doc_id"] == "d1"

    def test_list_empty(self, client):
        with patch(
            "argus.server.ingest.ingest_service.IngestService.list_documents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get("/v1/ingest/list")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_invalid_collection_filter_returns_422(self, client):
        resp = client.get("/v1/ingest/list?collection=garbage")
        assert resp.status_code == 422


# ── DELETE /v1/ingest/{doc_id} ────────────────────────────────────────────────

class TestDeleteDocument:
    def test_delete_success(self, client):
        with patch(
            "argus.server.ingest.ingest_service.IngestService.delete",
            new_callable=AsyncMock,
            return_value={"doc_id": "d1", "status": "deleted"},
        ):
            resp = client.delete("/v1/ingest/d1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_not_found_returns_404(self, client):
        with patch(
            "argus.server.ingest.ingest_service.IngestService.delete",
            new_callable=AsyncMock,
            side_effect=ValueError("Document not found"),
        ):
            resp = client.delete("/v1/ingest/missing-doc")
        assert resp.status_code == 404
