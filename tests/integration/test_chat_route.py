"""
Integration tests for the chat router.

The LangGraph graph and all LLM/vector store calls are mocked so no real
infrastructure is needed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from argus.main import app


_DUMMY_STATE = {
    "query": "", "session_id": "", "skill": "all_campaigns", "client_id": "internal",
    "allowed_collections": ["campaign_performance"], "llm": None, "vector_store": None,
    "prompt_manager": None, "redis_url": "redis://localhost:6379",
    "redis_cfg": MagicMock(session_ttl=1800, session_max_messages=20),
    "system_prompt": "", "history": [], "rewritten_query": "",
    "chunks": [], "answer": "", "citations": [], "blocked": False, "block_reason": "",
}


def _make_state(**overrides):
    return {**_DUMMY_STATE, **overrides}


@pytest.fixture(autouse=True)
def _patch_arq():
    app.state.arq_pool = None


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Non-streaming ─────────────────────────────────────────────────────────────

class TestChatJSON:
    def test_basic_query_returns_answer(self, client):
        final_state = {
            **_DUMMY_STATE,
            "answer": "Summer Push had the best ROAS at 4.2x.",
            "citations": [{"index": 1, "source_file": "q3.csv", "score": 0.91}],
        }
        with patch("argus.server.chat.chat_router._build_initial_state", return_value=_DUMMY_STATE), \
             patch("argus.server.chat.chat_router.compiled_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=final_state)
            resp = client.post(
                "/v1/chat",
                json={"message": "Which campaigns had the best ROAS?"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "ROAS" in body["answer"]
        assert len(body["sources"]) == 1
        assert "session_id" in body

    def test_session_id_preserved(self, client):
        final_state = {**_DUMMY_STATE, "answer": "Budget is $50k.", "citations": []}
        with patch("argus.server.chat.chat_router._build_initial_state", return_value=_DUMMY_STATE), \
             patch("argus.server.chat.chat_router.compiled_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=final_state)
            resp = client.post(
                "/v1/chat",
                json={"message": "What is the budget?", "session_id": "test-session-001"},
            )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "test-session-001"

    def test_blocked_request_returns_403(self, client):
        final_state = {
            **_DUMMY_STATE, "answer": "", "citations": [],
            "blocked": True, "block_reason": "No collections accessible.",
        }
        with patch("argus.server.chat.chat_router._build_initial_state", return_value=_DUMMY_STATE), \
             patch("argus.server.chat.chat_router.compiled_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=final_state)
            resp = client.post("/v1/chat", json={"message": "tell me everything"})
        assert resp.status_code == 403

    def test_empty_message_rejected(self, client):
        resp = client.post("/v1/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message_rejected(self, client):
        resp = client.post("/v1/chat", json={})
        assert resp.status_code == 422


# ── RAG graph unit tests ──────────────────────────────────────────────────────

class TestRagNodes:
    @pytest.mark.asyncio
    async def test_auth_skill_gate_passes_with_collections(self):
        from argus.server.chat.rag_graph import auth_skill_gate
        state = {"allowed_collections": ["campaign_performance"], "skill": "all_campaigns"}
        result = await auth_skill_gate(state)
        assert not result.get("blocked")

    @pytest.mark.asyncio
    async def test_auth_skill_gate_blocks_empty_collections(self):
        from argus.server.chat.rag_graph import auth_skill_gate
        state = {"allowed_collections": [], "skill": "all_campaigns"}
        result = await auth_skill_gate(state)
        assert result.get("blocked") is True

    @pytest.mark.asyncio
    async def test_prompt_selection_returns_string(self):
        from argus.server.chat.rag_graph import prompt_selection
        mock_pm = MagicMock()
        mock_pm.get.return_value = "You are a marketing analyst."
        state = {"prompt_manager": mock_pm, "skill": "all_campaigns", "client_id": "acme"}
        result = await prompt_selection(state)
        assert isinstance(result["system_prompt"], str)
        assert len(result["system_prompt"]) > 0

    @pytest.mark.asyncio
    async def test_query_rewrite_returns_string(self):
        from argus.server.chat.rag_graph import query_rewrite
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value="best performing campaigns by ROAS")
        state = {"llm": mock_llm, "query": "which campaigns did well?"}
        result = await query_rewrite(state)
        assert result["rewritten_query"] == "best performing campaigns by ROAS"

    @pytest.mark.asyncio
    async def test_query_rewrite_falls_back_on_error(self):
        from argus.server.chat.rag_graph import query_rewrite
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(side_effect=RuntimeError("LLM down"))
        state = {"llm": mock_llm, "query": "original query"}
        result = await query_rewrite(state)
        assert result["rewritten_query"] == "original query"

    @pytest.mark.asyncio
    async def test_reranking_top5(self):
        from argus.server.chat.rag_graph import reranking
        chunks = [{"content": f"chunk {i}", "score": float(i)} for i in range(10)]
        state = {"chunks": chunks, "rewritten_query": "test", "query": "test"}
        with patch("argus.server.chat.rag_graph._get_reranker", return_value=None):
            result = await reranking(state)
        assert len(result["chunks"]) == 5

    @pytest.mark.asyncio
    async def test_response_format_builds_citations(self):
        from argus.server.chat.rag_graph import response_format
        chunks = [
            {
                "content": "text",
                "score": 0.9,
                "collection": "monthly_reports",
                "metadata": {"source_file": "q3.pdf", "page": 2, "client_id": "acme"},
            }
        ]
        state = {"chunks": chunks}
        result = await response_format(state)
        assert len(result["citations"]) == 1
        assert result["citations"][0]["source_file"] == "q3.pdf"
        assert result["citations"][0]["page"] == 2

    @pytest.mark.asyncio
    async def test_llm_generation_uses_context(self):
        from argus.server.chat.rag_graph import llm_generation
        mock_llm = MagicMock()
        mock_llm.achat = AsyncMock(return_value="Summer Push had ROAS 4.2x")
        state = {
            "llm": mock_llm,
            "chunks": [{"content": "Summer Push ROAS=4.2", "metadata": {}, "score": 0.9}],
            "history": [],
            "rewritten_query": "best ROAS campaign",
            "query": "best ROAS",
            "system_prompt": "You are helpful.",
        }
        result = await llm_generation(state)
        assert "Summer Push" in result["answer"]
        # Verify context was passed to LLM
        call_messages = mock_llm.achat.call_args.args[0]
        assert any("Summer Push" in m["content"] for m in call_messages)
