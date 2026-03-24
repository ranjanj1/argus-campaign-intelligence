from __future__ import annotations

"""
RAG node functions — each function maps ArgusState → dict of updated fields.

Node execution order (defined in chat_orchestrator.py):
  auth_skill_gate → prompt_selection → session_load → query_rewrite
  → rag_retrieval → reranking → llm_generation → session_save → response_format

Guards:
  - auth_skill_gate raises HTTP 403 if allowed_collections is empty.
  - Guardrail nodes (input/output) will be inserted here once built.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from argus.components.cache.semantic_cache import SemanticCache
from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.graph_store.graph_queries import (
    GET_CAMPAIGN_CONTEXT,
    GET_TOP_CAMPAIGNS_BY_METRIC,
    GET_SEGMENTS_FOR_CAMPAIGNS,
    GET_RELATED_CAMPAIGNS,
)
from argus.components.guardrails.guardrail_component import GuardrailComponent
from argus.components.llm.llm_component import LLMComponent
from argus.components.prompt_manager.prompt_manager import PromptManager
from argus.components.vector_store.vector_store_component import VectorStoreComponent
from argus.di import get_injector, get_settings

logger = logging.getLogger(__name__)

# ArgusState is a TypedDict — node functions accept plain dict at runtime.
# Type alias for documentation only (no import to avoid circular dep).
_State = dict

# ── Redis session helpers ──────────────────────────────────────────────────────

async def _get_redis() -> aioredis.Redis:
    """Create a per-call Redis client from settings."""
    return aioredis.from_url(
        get_settings().redis.url, encoding="utf-8", decode_responses=True
    )


async def _session_key(session_id: str) -> str:
    return f"argus:session:{session_id}"


# ── Node 1: auth_skill_gate ───────────────────────────────────────────────────

async def auth_skill_gate(state: dict) -> dict:
    """
    Verify the identity has at least one allowed collection.
    Sets blocked=True if not (shouldn't happen with valid JWT; belt+suspenders).
    """
    if not state.get("allowed_collections"):
        logger.warning("auth_skill_gate: no allowed collections for skill=%s", state.get("skill"))
        return {"blocked": True, "block_reason": "No collections accessible for this skill."}
    return {}


# ── Node 2: input_guardrail ───────────────────────────────────────────────────

async def input_guardrail(state: dict) -> dict:
    """
    Run input-side safety checks before any retrieval or LLM calls.

    Checks (each individually togglable via GuardrailSettings):
      - token_limit     : rejects oversized queries
      - input_toxicity  : rejects toxic/harmful content
      - ban_topics      : rejects forbidden topic keywords
      - anonymize_pii   : replaces PII in query (non-blocking)

    Sets blocked=True on failure; PII-anonymized query replaces state["query"].
    """
    try:
        guardrails = get_injector().get(GuardrailComponent)
    except Exception:
        return {}

    result = guardrails.check_input(
        query=state["query"],
        client_id=state["client_id"],
    )

    if not result.passed:
        logger.warning("input_guardrail blocked: %s", result.reason)
        return {"blocked": True, "block_reason": result.reason}

    # Apply PII-anonymized query if changed
    if result.modified_text and result.modified_text != state["query"]:
        return {"query": result.modified_text}

    return {}


# ── Node 3 (inserted): output_guardrail ───────────────────────────────────────

async def output_guardrail(state: dict) -> dict:
    """
    Run output-side safety checks after LLM generation.

    Checks (each individually togglable via GuardrailSettings):
      - client_isolation : blocks if any chunk belongs to a different client
      - output_toxicity  : blocks toxic LLM answers

    Sets blocked=True on failure.
    """
    try:
        guardrails = get_injector().get(GuardrailComponent)
    except Exception:
        return {}

    result = guardrails.check_output(
        answer=state.get("answer", ""),
        chunks=state.get("chunks", []),
        client_id=state["client_id"],
    )

    if not result.passed:
        logger.warning("output_guardrail blocked: %s", result.reason)
        return {"blocked": True, "block_reason": result.reason}

    return {}


# ── Cache lookup / store ──────────────────────────────────────────────────────

async def cache_lookup(state: dict) -> dict:
    """
    Check the semantic cache before running the full RAG pipeline.

    HIT  → sets answer, citations, cache_hit=True  (graph routes to session_save)
    MISS → sets cache_hit=False                     (graph routes to prompt_selection)
    """
    try:
        cache = get_injector().get(SemanticCache)
    except Exception:
        return {"cache_hit": False}

    try:
        hit = await cache.get(
            query=state["query"],
            skill=state["skill"],
            client_id=state["client_id"],
        )
        if hit is not None:
            return {
                "answer": hit.get("answer", ""),
                "citations": hit.get("citations", []),
                "cache_hit": True,
            }
    except Exception as exc:
        logger.warning("cache_lookup failed (%s) — proceeding without cache", exc)

    return {"cache_hit": False}


async def cache_store(state: dict) -> dict:
    """
    Persist the answer + citations to the semantic cache after a MISS.
    Non-blocking — errors are logged and ignored.
    """
    try:
        cache = get_injector().get(SemanticCache)
    except Exception:
        return {}

    try:
        await cache.set(
            query=state["query"],
            skill=state["skill"],
            client_id=state["client_id"],
            response={
                "answer": state.get("answer", ""),
                "citations": state.get("citations", []),
            },
        )
    except Exception as exc:
        logger.warning("cache_store failed: %s", exc)

    return {}


# ── Node 2 (original): prompt_selection ───────────────────────────────────────

async def prompt_selection(state: dict) -> dict:
    """Pick the system prompt for the client's skill via PromptManager."""
    pm = get_injector().get(PromptManager)
    system_prompt = pm.get(
        skill=state["skill"],
        client_id=state["client_id"],
    )
    return {"system_prompt": system_prompt}


# ── Node 3: session_load ──────────────────────────────────────────────────────

async def session_load(state: dict) -> dict:
    """
    Fetch the last N messages for this session from Redis.
    Returns empty list if session doesn't exist yet.
    """
    cfg = get_settings().redis
    r = await _get_redis()
    try:
        key = await _session_key(state["session_id"])
        raw = await r.get(key)
        history = json.loads(raw) if raw else []
        # Enforce max_messages cap
        max_msgs = cfg.session_max_messages
        history = history[-max_msgs:] if len(history) > max_msgs else history
        return {"history": history}
    except Exception as exc:
        logger.warning("session_load failed: %s", exc)
        return {"history": []}
    finally:
        await r.aclose()


# ── Node 4: query_rewrite ─────────────────────────────────────────────────────

_REWRITE_PROMPT = """You are a search query optimizer for a marketing analytics system.
Rewrite the user query to be more specific and retrieval-friendly.
Return ONLY the rewritten query — no explanation, no quotes.

Original query: {query}
Rewritten query:"""


async def query_rewrite(state: dict) -> dict:
    """
    Use the LLM to expand and clarify the query for better semantic retrieval.
    Falls back to original query on error.
    """
    llm = get_injector().get(LLMComponent)
    query = state["query"]
    try:
        rewritten = await llm.acomplete(_REWRITE_PROMPT.format(query=query))
        rewritten = rewritten.strip().strip('"').strip("'")
        logger.debug("query_rewrite: '%s' → '%s'", query, rewritten)
        return {"rewritten_query": rewritten or query}
    except Exception as exc:
        logger.warning("query_rewrite failed (%s) — using original", exc)
        return {"rewritten_query": query}


# ── Graph retrieval helper ────────────────────────────────────────────────────

# Keywords that trigger metric-specific graph queries
_METRIC_KEYWORDS: dict[str, str] = {
    "roas": "roas",
    "return on ad": "roas",
    "ctr": "ctr",
    "click-through": "ctr",
    "cpa": "cpa",
    "cost per acquisition": "cpa",
    "cost per action": "cpa",
    "conversion rate": "conversion_rate",
    "conversion": "conversion_rate",
}


def _chunk_from_graph(text: str, client_id: str, score: float = 0.05) -> dict:
    """Wrap a Neo4j result string into the same chunk format as pgvector results."""
    return {
        "content": text,
        "metadata": {
            "source_file": "neo4j_graph",
            "client_id": client_id,
            "collection": "graph",
            "page": None,
        },
        "score": score,
        "collection": "graph",
    }


async def _graph_retrieval(client_id: str, query: str) -> list[dict]:
    """
    Query Neo4j for structured campaign context and return as text chunks.

    Always runs:
      - Campaign overview (name, channel, status, segments, metrics)

    Conditionally runs based on query keywords:
      - Top campaigns by metric (ROAS, CTR, CPA, conversion_rate)
      - Audience segments across campaigns
    """
    try:
        graph = get_injector().get(GraphStoreComponent)
    except Exception as exc:
        logger.warning("GraphStoreComponent unavailable: %s", exc)
        return []

    graph_chunks: list[dict] = []
    query_lower = query.lower()

    # ── 1. Campaign overview (always) ─────────────────────────────────────────
    try:
        rows = await graph.query(
            GET_CAMPAIGN_CONTEXT,
            {"client_id": client_id, "limit": 15},
        )
        if rows:
            lines = []
            for r in rows:
                segments = ", ".join(r.get("segments") or []) or "none"
                metrics = "; ".join(
                    f"{m['type']}={m['value']}"
                    for m in (r.get("metrics") or [])
                    if m.get("type") and m.get("value") is not None
                ) or "none"
                lines.append(
                    f"Campaign: {r['campaign_name']} | "
                    f"Channel: {r['channel']} | "
                    f"Status: {r['status']} | "
                    f"Segments: {segments} | "
                    f"Metrics: {metrics}"
                )
            text = (
                f"Graph context — campaigns for client '{client_id}':\n"
                + "\n".join(lines)
            )
            graph_chunks.append(_chunk_from_graph(text, client_id, score=0.06))
            logger.debug("graph_retrieval: campaign overview — %d rows", len(rows))
    except Exception as exc:
        logger.warning("graph_retrieval: campaign overview failed: %s", exc)

    # ── 2. Top campaigns by metric (if query mentions one) ────────────────────
    matched_metric: str | None = None
    for keyword, metric_type in _METRIC_KEYWORDS.items():
        if keyword in query_lower:
            matched_metric = metric_type
            break

    if matched_metric:
        try:
            rows = await graph.query(
                GET_TOP_CAMPAIGNS_BY_METRIC,
                {"client_id": client_id, "metric_type": matched_metric, "limit": 10},
            )
            if rows:
                lines = [
                    f"{r['campaign_name']}: {matched_metric}={r['metric_value']} "
                    f"(period: {r['period']})"
                    for r in rows
                ]
                text = (
                    f"Graph context — top campaigns by {matched_metric} "
                    f"for client '{client_id}':\n" + "\n".join(lines)
                )
                graph_chunks.append(_chunk_from_graph(text, client_id, score=0.08))
                logger.debug(
                    "graph_retrieval: metric=%s — %d rows", matched_metric, len(rows)
                )
        except Exception as exc:
            logger.warning("graph_retrieval: metric query failed: %s", exc)

    # ── 3. Audience segments (if query mentions audience/segment/targeting) ───
    audience_keywords = {"audience", "segment", "target", "demographic", "who"}
    if any(kw in query_lower for kw in audience_keywords):
        try:
            rows = await graph.query(
                GET_SEGMENTS_FOR_CAMPAIGNS,
                {"client_id": client_id},
            )
            if rows:
                lines = [
                    f"Segment: {r['segment_name']} | "
                    f"Platform: {r['platform']} | "
                    f"Campaigns: {', '.join(r.get('campaigns') or [])}"
                    for r in rows
                ]
                text = (
                    f"Graph context — audience segments for client '{client_id}':\n"
                    + "\n".join(lines)
                )
                graph_chunks.append(_chunk_from_graph(text, client_id, score=0.06))
                logger.debug(
                    "graph_retrieval: segments — %d rows", len(rows)
                )
        except Exception as exc:
            logger.warning("graph_retrieval: segment query failed: %s", exc)

    return graph_chunks


# ── Node 5: rag_retrieval ─────────────────────────────────────────────────────

async def rag_retrieval(state: dict) -> dict:
    """
    Hybrid retrieval: pgvector (dense + sparse) + Neo4j graph context.

    pgvector:  semantic similarity search across allowed collections
    Neo4j:     structured campaign/segment/metric context from the graph

    Results are merged — graph chunks are appended after vector chunks so
    the reranker can score them alongside each other.
    """
    from argus.utils.skills import ClientSkill

    vector_store = get_injector().get(VectorStoreComponent)
    rewritten_query = state.get("rewritten_query") or state["query"]
    collections = state["allowed_collections"]
    client_id = state["client_id"]

    # single_client and narrow skills filter by client_id
    filters: dict[str, Any] = {}
    if state["skill"] != ClientSkill.ALL_CAMPAIGNS.value:
        filters = {"client_id": client_id}

    # ── pgvector search ───────────────────────────────────────────────────────
    vector_chunks: list[dict] = []
    try:
        vector_chunks = await vector_store.hybrid_search(
            query_text=rewritten_query,
            collections=collections,
            filters=filters,
            top_k=10,
        )
        logger.debug("rag_retrieval: pgvector returned %d chunks", len(vector_chunks))
    except Exception as exc:
        logger.error("rag_retrieval: pgvector failed: %s", exc)

    # ── Neo4j graph search ────────────────────────────────────────────────────
    graph_chunks: list[dict] = []
    try:
        graph_chunks = await _graph_retrieval(client_id, rewritten_query)
        logger.debug("rag_retrieval: graph returned %d chunks", len(graph_chunks))
    except Exception as exc:
        logger.warning("rag_retrieval: graph retrieval failed: %s", exc)

    return {"chunks": vector_chunks + graph_chunks}
    #return {"chunks": graph_chunks}



# ── Node 6: reranking ─────────────────────────────────────────────────────────

_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None   # module-level lazy singleton


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(_RERANKER_MODEL)
            logger.info("CrossEncoder reranker loaded: %s", _RERANKER_MODEL)
        except Exception as exc:
            logger.warning("CrossEncoder unavailable (%s) — using score-based ranking", exc)
            _reranker = False   # sentinel: don't retry
    return _reranker if _reranker else None


async def reranking(state: dict) -> dict:
    """
    Re-score top-10 chunks down to top-5.
    Uses CrossEncoder if available, otherwise keeps top-5 by RRF score.
    """
    import asyncio

    chunks = state.get("chunks", [])
    query = state.get("rewritten_query") or state["query"]
    top_n = 5

    if not chunks:
        return {"chunks": []}

    reranker = _get_reranker()
    if reranker is not None and chunks:
        try:
            loop = asyncio.get_event_loop()
            pairs = [(query, c["content"]) for c in chunks]
            scores = await loop.run_in_executor(
                None, lambda: reranker.predict(pairs).tolist()
            )
            ranked = sorted(
                zip(scores, chunks), key=lambda x: x[0], reverse=True
            )
            reranked = [c for _, c in ranked[:top_n]]
            return {"chunks": reranked}
        except Exception as exc:
            logger.warning("reranking failed (%s) — using top-%d by score", exc, top_n)

    return {"chunks": chunks[:top_n]}


# ── Node 7: llm_generation ────────────────────────────────────────────────────

_CONTEXT_TEMPLATE = """CONTEXT DOCUMENTS:
{context}

---
CONVERSATION HISTORY:
{history}

---
USER QUESTION: {question}"""


async def llm_generation(state: dict) -> dict:
    """
    Generate the final answer using:
      - system prompt (skill-specific)
      - retrieved chunks as context
      - conversation history
      - the (rewritten) question
    """
    llm = get_injector().get(LLMComponent)
    chunks = state.get("chunks", [])
    history = state.get("history", [])
    question = state.get("rewritten_query") or state["query"]
    system_prompt = state.get("system_prompt", "You are a helpful marketing analytics assistant.")

    # Format context
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            source = meta.get("source_file", "unknown")
            page = meta.get("page", "")
            page_str = f" (p.{page})" if page else ""
            context_parts.append(f"[{i}] Source: {source}{page_str}\n{chunk['content']}")
        context_str = "\n\n".join(context_parts)
    else:
        context_str = "No relevant documents found."

    # Format history
    history_str = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history[-6:]
    ) if history else "No prior conversation."

    user_content = _CONTEXT_TEMPLATE.format(
        context=context_str,
        history=history_str,
        question=question,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    for i, chunk in enumerate(chunks, 1):
        src = chunk.get("metadata", {}).get("source", "pgvector")
        label = "GRAPH" if src == "neo4j" else "VECTOR"
        logger.info("[%d][%s] %s", i, label, chunk["content"][:300])
    logger.info("LLM INPUT ▼\n%s\n---\n%s", messages[0]["content"], messages[1]["content"])

    try:
        answer = await llm.achat(messages)
    except Exception as exc:
        logger.error("llm_generation failed: %s", exc)
        answer = "I encountered an error generating a response. Please try again."

    return {"answer": answer}


# ── Node 8: session_save ──────────────────────────────────────────────────────

async def session_save(state: dict) -> dict:
    """
    Append the Q+A turn to Redis. Enforces max_messages cap. Resets TTL.
    """
    cfg = get_settings().redis
    r = await _get_redis()
    try:
        key = await _session_key(state["session_id"])
        history = list(state.get("history", []))
        history.append({"role": "user", "content": state["query"]})
        history.append({"role": "assistant", "content": state.get("answer", "")})
        # Enforce cap
        max_msgs = cfg.session_max_messages
        history = history[-max_msgs:]
        await r.set(key, json.dumps(history), ex=cfg.session_ttl)
    except Exception as exc:
        logger.warning("session_save failed: %s", exc)
    finally:
        await r.aclose()
    return {}


# ── Node 9: response_format ───────────────────────────────────────────────────

async def response_format(state: dict) -> dict:
    """
    Build citation objects from the retrieved chunks.
    On a cache HIT, citations are already populated — return early.
    """
    if state.get("cache_hit"):
        return {}   # citations already set by cache_lookup

    chunks = state.get("chunks", [])
    citations = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        citations.append({
            "index": i,
            "source_file": meta.get("source_file", ""),
            "collection": chunk.get("collection", meta.get("collection", "")),
            "page": meta.get("page"),
            "client_id": meta.get("client_id", ""),
            "score": round(chunk.get("score", 0.0), 4),
            "excerpt": chunk.get("content", ""),
        })
    return {"citations": citations}
