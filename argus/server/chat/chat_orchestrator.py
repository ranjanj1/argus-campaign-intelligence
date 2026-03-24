from __future__ import annotations

"""
Chat orchestrator — LangGraph StateGraph definition.

ArgusState flows through 9 nodes:
  auth_skill_gate → prompt_selection → session_load → query_rewrite
  → rag_retrieval → reranking → llm_generation → session_save → response_format

Conditional edge after auth_skill_gate:
  blocked=True  → END  (HTTP 403 raised by router)
  blocked=False → prompt_selection (normal path)

All slow component references (LLM, vector store, etc.) are stored in state
so nodes don't need to reach into the DI container at graph-compile time.
"""

from typing import List, TypedDict

from langgraph.graph import END, StateGraph

from argus.server.chat.rag_graph import (
    auth_skill_gate,
    input_guardrail,
    output_guardrail,
    cache_lookup,
    cache_store,
    llm_generation,
    prompt_selection,
    query_rewrite,
    rag_retrieval,
    reranking,
    response_format,
    session_load,
    session_save,
)


# ── State definition ──────────────────────────────────────────────────────────

class ArgusState(TypedDict, total=False):
    # ── Identity (set by router before graph invocation) ──────────────────────
    query: str
    session_id: str
    skill: str                       # ClientSkill.value string
    client_id: str
    allowed_collections: List[str]

    # ── Pipeline intermediates ────────────────────────────────────────────────
    system_prompt: str
    history: List[dict]
    rewritten_query: str
    chunks: List[dict]
    answer: str
    citations: List[dict]
    blocked: bool
    block_reason: str
    cache_hit: bool


# ── Conditional edge ──────────────────────────────────────────────────────────

def _should_continue(state: ArgusState) -> str:
    """Route to END if blocked, otherwise continue."""
    return "blocked" if state.get("blocked") else "continue"


def _cache_route(state: ArgusState) -> str:
    """After cache_lookup: skip full pipeline on HIT, run it on MISS."""
    return "hit" if state.get("cache_hit") else "miss"


def _cache_write_route(state: ArgusState) -> str:
    """After response_format: store in cache on MISS, skip on HIT."""
    return "skip" if state.get("cache_hit") else "store"


# ── Graph factory ─────────────────────────────────────────────────────────────

def build_graph():
    """
    Compile and return the Argus LangGraph StateGraph.

    Called once at app startup; the compiled graph is stored on app.state
    and reused for every request.
    """
    g = StateGraph(ArgusState)

    # Register nodes
    g.add_node("auth_skill_gate", auth_skill_gate)
    g.add_node("input_guardrail", input_guardrail)
    g.add_node("cache_lookup", cache_lookup)
    g.add_node("prompt_selection", prompt_selection)
    g.add_node("session_load", session_load)
    g.add_node("query_rewrite", query_rewrite)
    g.add_node("rag_retrieval", rag_retrieval)
    g.add_node("reranking", reranking)
    g.add_node("llm_generation", llm_generation)
    g.add_node("output_guardrail", output_guardrail)
    g.add_node("session_save", session_save)
    g.add_node("response_format", response_format)
    g.add_node("cache_store", cache_store)

    # Entry point
    g.set_entry_point("auth_skill_gate")

    # auth → input guardrail
    g.add_conditional_edges(
        "auth_skill_gate",
        _should_continue,
        {"blocked": END, "continue": "input_guardrail"},
    )

    # input guardrail → cache_lookup
    g.add_conditional_edges(
        "input_guardrail",
        _should_continue,
        {"blocked": END, "continue": "cache_lookup"},
    )

    # cache_lookup: HIT → session_save (skip full pipeline)
    #               MISS → prompt_selection (run full pipeline)
    g.add_conditional_edges(
        "cache_lookup",
        _cache_route,
        {"hit": "session_save", "miss": "prompt_selection"},
    )

    # Full pipeline (MISS path)
    g.add_edge("prompt_selection", "session_load")
    g.add_edge("session_load", "query_rewrite")
    g.add_edge("query_rewrite", "rag_retrieval")
    g.add_edge("rag_retrieval", "reranking")
    g.add_edge("reranking", "llm_generation")

    g.add_conditional_edges(
        "llm_generation",
        _should_continue,
        {"blocked": END, "continue": "output_guardrail"},
    )

    g.add_conditional_edges(
        "output_guardrail",
        _should_continue,
        {"blocked": END, "continue": "session_save"},
    )

    # session_save and response_format shared by both HIT and MISS paths
    g.add_edge("session_save", "response_format")

    # After response_format: store in cache on MISS, skip on HIT
    g.add_conditional_edges(
        "response_format",
        _cache_write_route,
        {"store": "cache_store", "skip": END},
    )

    g.add_edge("cache_store", END)

    return g.compile()


# Module-level compiled graph — imported by chat_router
compiled_graph = build_graph()
