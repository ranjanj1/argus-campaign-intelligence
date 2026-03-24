from __future__ import annotations

"""
Chat router — POST /v1/chat

Supports two response modes controlled by the `stream` query parameter:
  stream=false (default) → JSON response { answer, sources, session_id }
  stream=true            → Server-Sent Events, one token per event

SSE event format:
  event: token        data: {"token": "..."}
  event: done         data: {"answer": "...", "sources": [...], "session_id": "..."}
  event: error        data: {"detail": "..."}
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from argus.server.chat.chat_orchestrator import compiled_graph
from argus.server.utils.auth import require_auth
from argus.di import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    session_id: Optional[str] = Field(None, description="Resume an existing session")
    stream: bool = Field(False, description="Enable SSE streaming")
    client_id: Optional[str] = Field(None, description="Dev-mode client override")


class ChatResponse(BaseModel):
    answer: str
    sources: list
    session_id: str


# ── State builder ─────────────────────────────────────────────────────────────

def _build_initial_state(
    message: str,
    session_id: str,
    identity: dict,
) -> dict[str, Any]:
    """
    Assemble the initial ArgusState dict.
    Only plain, picklable values go in state — components are fetched from
    the DI container directly inside each graph node.
    """
    return {
        # Identity
        "query": message,
        "session_id": session_id,
        "skill": identity["skill"].value,
        "client_id": identity["client_id"],
        "allowed_collections": identity["allowed_collections"],
        # Pipeline intermediates — empty at start
        "system_prompt": "",
        "history": [],
        "rewritten_query": "",
        "chunks": [],
        "answer": "",
        "citations": [],
        "blocked": False,
        "block_reason": "",
        "cache_hit": False,
    }


# ── POST /v1/chat ─────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    request: ChatRequest,
    identity: dict = Depends(require_auth),
):
    """
    Main chat endpoint.

    - Non-streaming (default): returns JSON immediately after full generation.
    - Streaming (stream=true): returns SSE stream with token-by-token output.
    """
    session_id = request.session_id or uuid.uuid4().hex
    # In dev mode (auth disabled), allow frontend to override client_id
    if request.client_id and not get_settings().auth.enabled:
        identity = {**identity, "client_id": request.client_id}
    initial_state = _build_initial_state(request.message, session_id, identity)

    if request.stream:
        return EventSourceResponse(
            _stream_response(initial_state, session_id),
            media_type="text/event-stream",
        )

    return await _json_response(initial_state, session_id)


# ── Non-streaming path ────────────────────────────────────────────────────────

async def _json_response(initial_state: dict, session_id: str) -> dict:
    """Run the full graph and return a JSON-serialisable dict."""
    final_state = await compiled_graph.ainvoke(initial_state)

    if final_state.get("blocked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=final_state.get("block_reason", "Request blocked."),
        )

    return {
        "answer": final_state.get("answer", ""),
        "sources": final_state.get("citations", []),
        "session_id": session_id,
    }


# ── Streaming path ────────────────────────────────────────────────────────────

async def _stream_response(
    initial_state: dict, session_id: str
) -> AsyncIterator[dict]:
    """
    SSE generator — single graph pass, no double invocation.

    Strategy:
      - astream_events yields 'on_chat_model_stream' for each LLM token.
      - 'on_chain_end' events for individual nodes carry their output delta;
        we capture 'llm_generation' and 'response_format' outputs explicitly.
      - After iteration, emit a final 'done' event with the full response.
    """
    answer_parts: list[str] = []
    citations: list = []
    blocked = False
    block_reason = ""

    try:
        async for event in compiled_graph.astream_events(
            initial_state, version="v1"
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Stream individual LLM tokens to the client (when LLM supports native streaming)
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    answer_parts.append(chunk.content)
                    yield {
                        "event": "token",
                        "data": json.dumps({"token": chunk.content}),
                    }

            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output") or {}

                if name in ("auth_skill_gate", "input_guardrail", "output_guardrail") \
                        and output.get("blocked"):
                    blocked = True
                    block_reason = output.get("block_reason", "Request blocked.")

                elif name == "llm_generation" and not answer_parts:
                    # LLM node returned full answer (no native streaming) — emit word by word
                    answer = output.get("answer", "")
                    if answer:
                        for word in answer.split(" "):
                            token = word + " "
                            answer_parts.append(token)
                            yield {
                                "event": "token",
                                "data": json.dumps({"token": token}),
                            }

                elif name == "response_format":
                    citations = output.get("citations", [])

    except Exception as exc:
        logger.exception("Streaming error: %s", exc)
        yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
        return

    if blocked:
        yield {
            "event": "error",
            "data": json.dumps({"detail": block_reason}),
        }
        return

    yield {
        "event": "done",
        "data": json.dumps({
            "answer": "".join(answer_parts),
            "sources": citations,
            "session_id": session_id,
        }),
    }
