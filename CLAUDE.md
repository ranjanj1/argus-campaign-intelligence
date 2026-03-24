# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Argus** — a production-grade **GraphRAG** backend for 2060 Digital (marketing agency). Enables analysts and clients to ask plain-English questions across campaign data (ad copy, audience segments, performance reports, budget history) and receive grounded, cited answers via a FastAPI + LangGraph + Qdrant + Neo4j pipeline.

> **Status:** Implementation phase. Full design in `argus_plan_v2.md` (authoritative). `argus_plan.docx` is the original v1 — superseded.

---

## Commands

```bash
# Infrastructure (PostgreSQL/pgvector + Neo4j + Redis)
docker compose up postgres neo4j redis -d

# Ingest worker (ARQ — separate process)
poetry run python -m arq argus.components.ingest.ingest_worker.WorkerSettings

# Dev server (auth disabled, local LLM overrides)
ARGUS_PROFILES=develop poetry run python -m argus

# Lint
poetry run ruff check argus/

# Type check
poetry run mypy argus/

# All tests with coverage
poetry run pytest tests/ --cov=argus --cov-report=xml

# Single test file
poetry run pytest tests/unit/test_settings.py -v

# Ingest a document (dev)
curl -X POST http://localhost:8001/v1/ingest/file \
  -F 'file=@q3_report.pdf' \
  -F 'collection=campaign_performance' \
  -F 'client_id=client_acme'

# Chat query (dev, no auth)
curl -X POST http://localhost:8001/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Which campaigns had the best ROAS?", "session_id": "test-001"}'
```

---

## Architecture

### Three Independent Vertical Flows

```
CHAT FLOW                  INGEST FLOW                CONFIG FLOW
chat_router.py             ingest_router.py           settings.py
chat_orchestrator.py       ingest_service.py          settings_loader.py
rag_nodes.py               ingest_worker.py (ARQ)     settings.yaml
                           ingest_component.py
                           ingest_helper.py
                           entity_extractor.py  → Neo4j
                           table_chunker.py
```

### Planned Directory Layout

```
argus/
├── __main__.py             # uvicorn entrypoint
├── launcher.py             # FastAPI factory + DI wiring
├── main.py                 # app instance
├── di.py                   # injector DI container
├── paths.py                # filesystem path constants
├── settings/
│   ├── settings.py         # Pydantic config models
│   └── settings_loader.py  # YAML merge + ${ENV_VAR:default} substitution
├── components/
│   ├── llm/                # LLMComponent (OpenAI primary, Gemini/Bedrock/Ollama supported)
│   ├── embedding/          # EmbeddingComponent (nomic-embed-text-v1.5 default)
│   ├── vector_store/       # VectorStoreComponent (Qdrant) — dense + BM25
│   ├── graph_store/        # GraphStoreComponent (Neo4j) — entity relationships
│   ├── ingest/             # IngestHelper, IngestComponent, EntityExtractor, TableChunker, ARQ worker
│   ├── guardrails/         # GuardrailComponent (toxicity, ban topics, anonymizer)
│   ├── cache/              # SemanticCache (Redis embedding-similarity cache)
│   └── prompt_manager/     # PromptManager + per-skill YAML system prompts
├── server/
│   ├── utils/auth.py       # JWT validation middleware (AWS Cognito)
│   ├── chat/
│   │   ├── chat_router.py       # POST /v1/chat (SSE streaming + JSON)
│   │   ├── chat_orchestrator.py # LangGraph StateGraph definition (most important file)
│   │   └── rag_graph.py         # Node functions for each graph step
│   └── ingest/
│       ├── ingest_router.py     # POST /v1/ingest/file, GET /v1/ingest/list
│       └── ingest_service.py
└── utils/skills.py         # ClientSkill enum + JWT claim → allowed collections mapping
```

### The RAG Pipeline — LangGraph `StateGraph` (`chat_orchestrator.py`)

Each step is a **LangGraph node**; guardrail failures use conditional edges to route to the blocked path (HTTP 400/403) instead of continuing.

```
ArgusState: { query, session_id, skill, client_id, history,
              rewritten_query, chunks, answer, blocked, citations }
```

| # | Node | What it does |
|---|------|-------------|
| 1 | `auth_skill_gate` | JWT payload → `ClientSkill` enum → allowed Qdrant collections |
| 2 | `input_guardrail` | Toxicity (0.75), BanTopics (competitors), Anonymizer (PII), TokenLimit (10K) |
| 3 | `prompt_selection` | `PromptManager` picks YAML-defined system prompt for the skill (6 variants) |
| 4 | `session_load` | Redis: fetch last 20 messages, 30-min TTL |
| 5 | `query_rewrite` | LLM rewrites/expands raw query for better semantic retrieval |
| 6 | `rag_retrieval` | `FusionRetriever`: dense (nomic-embed) + BM25 sparse, top-K=10 |
| 7 | `reranking` | `cross-encoder/ms-marco` re-scores → top-N=5 |
| 8 | `llm_generation` | GPT-4o: system prompt + chunks + history + question |
| 9 | `output_guardrail` | Toxicity (0.70), NoRefusal, Sensitive data / cross-client leak |
| 10 | `session_save` | Redis: append Q+A, reset TTL, enforce 20-msg cap |
| 11 | `response_format` | `{ answer, sources[], session_id }` with file/page/date citations |

**Conditional edges:** Steps 2 and 9 branch to `END` (HTTP 400/403) on guardrail failure.

### Storage Responsibilities

| Store | Port | Purpose |
|-------|------|---------|
| PostgreSQL + pgvector | 5432 | Document chunks + dense vectors + FTS (tsvector) |
| Neo4j | 7687 | Entity graph: Client→Campaign→AdGroup→Audience→Metrics |
| Redis | 6379 | Sessions (30-min TTL), semantic cache (1-hr TTL), ARQ ingest queue |
| SQLite | local_data/ | Token usage + cost logs per client |
| Langfuse | cloud | LLM traces, feedback scores, prompt versioning |

### Configuration System

- Base config: `settings.yaml`; env overrides: `settings-develop.yaml`, `settings-test.yaml`, etc.
- Profile activated via `ARGUS_PROFILES=develop` env var
- All secrets use `${ENV_VAR:default}` substitution in YAML — never hardcode secrets
- Pydantic models in `settings/settings.py` validate config at startup

### Skill-Based Access Control

`argus/utils/skills.py` maps JWT claims → `ClientSkill` enum → allowed Qdrant collections. Each client can only query their own collections. Auth is disabled in the `develop` profile.

---

## Stack

| Concern | Choice |
|---------|--------|
| Web framework | FastAPI |
| Package manager | Poetry |
| Pipeline / agentic | LangGraph |
| Vector DB | **pgvector** (PostgreSQL + `langchain-postgres`) |
| Graph DB | **Neo4j** (`neo4j` driver + `langchain-neo4j`) |
| Default embedding | nomic-ai/nomic-embed-text-v1.5 |
| Entity extraction | spaCy + GLiNER |
| Primary LLM | OpenAI GPT-4o |
| Session + cache store | Redis |
| Ingest queue | ARQ (async Redis queue) |
| Auth | AWS Cognito + JWT RS256 |
| DI | injector |
| Observability | Langfuse |

---

## Key API Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/v1/chat` | JWT required — supports SSE streaming |
| POST | `/v1/completions` | JWT required — OpenAI-compatible |
| POST | `/v1/embeddings` | JWT required — vector generation |
| POST | `/v1/ingest/file` | JWT required — async background task |
| GET | `/v1/ingest/list` | JWT required |
| DELETE | `/v1/ingest/{doc_id}` | JWT required — remove from Qdrant |
| GET | `/health` | None — checks Qdrant + Redis liveness |
| GET | `/docs` | None |

---

## Recommended Reading Order (when code exists)

1. `settings.yaml` — config surface area
2. `argus/settings/settings.py` — Pydantic models
3. `argus/launcher.py` — app startup + DI wiring
4. `argus/utils/skills.py` — skill/collection mapping
5. `argus/server/utils/auth.py` — JWT validation
6. `argus/server/chat/chat_router.py` — entry point + SSE streaming
7. `argus/server/chat/chat_orchestrator.py` — **LangGraph StateGraph definition**
8. `argus/server/chat/rag_graph.py` — individual node implementations
9. `argus/components/ingest/ingest_helper.py` — file parsing
10. `argus/components/ingest/ingest_component.py` — chunk → embed → store

---

## Test Layout

```
tests/
├── unit/
│   ├── test_settings.py
│   ├── test_ingest_helper.py
│   ├── test_skills.py
│   └── test_guardrails.py
├── integration/
│   ├── test_ingest_route.py
│   ├── test_chat_route.py
│   └── test_session_manager.py
└── conftest.py
```

Integration tests hit real Qdrant + Redis (spin up with docker compose). Unit tests mock the injector container.
