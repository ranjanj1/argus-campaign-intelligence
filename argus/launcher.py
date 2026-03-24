from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from argus.di import get_injector
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    injector = get_injector()
    settings = injector.get(Settings)

    app = FastAPI(
        title="Argus — Campaign Intelligence System",
        version="2.0.0",
        description="GraphRAG backend for campaign data intelligence",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Startup: initialise pgvector extension + collections ─────────────────
    @app.on_event("startup")
    async def _startup() -> None:
        from arq.connections import RedisSettings as ArqRedisSettings, create_pool
        from argus.components.vector_store.vector_store_component import VectorStoreComponent
        from argus.components.graph_store.graph_store_component import GraphStoreComponent

        # pgvector extension + collection tables
        vector_store = injector.get(VectorStoreComponent)
        try:
            await vector_store.initialize()
        except Exception as exc:
            logger.warning("pgvector init skipped (DB may not be running): %s", exc)

        # Neo4j schema (constraints + indexes)
        graph_store = injector.get(GraphStoreComponent)
        try:
            await graph_store.init_schema()
        except Exception as exc:
            logger.warning("Neo4j schema init skipped (DB may not be running): %s", exc)

        # ARQ pool — used by IngestService to enqueue background jobs
        try:
            app.state.arq_pool = await create_pool(
                ArqRedisSettings(
                    host=settings.redis.host,
                    port=settings.redis.port,
                )
            )
            logger.info("ARQ pool ready")
        except Exception as exc:
            app.state.arq_pool = None
            logger.warning("ARQ pool unavailable (worker jobs will run inline): %s", exc)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        if getattr(app.state, "arq_pool", None):
            await app.state.arq_pool.aclose()

    # ── Routers ───────────────────────────────────────────────────────────────
    from argus.server.ingest.ingest_router import router as ingest_router
    from argus.server.chat.chat_router import router as chat_router
    from argus.server.collections.collections_router import router as collections_router
    from argus.server.auth.auth_router import router as auth_router
    app.include_router(auth_router)
    app.include_router(ingest_router)
    app.include_router(chat_router)
    app.include_router(collections_router)

    # ── Health endpoint ───────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health(request: Request) -> JSONResponse:
        """Liveness probe — checks auth config and DB connectivity."""
        from argus.components.vector_store.vector_store_component import VectorStoreComponent
        from argus.components.graph_store.graph_store_component import GraphStoreComponent

        vector_store = injector.get(VectorStoreComponent)
        graph_store = injector.get(GraphStoreComponent)

        checks: dict = {"status": "ok", "version": "2.0.0",
                        "auth_enabled": settings.auth.enabled}

        try:
            await vector_store.ping()
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            checks["status"] = "degraded"

        try:
            await graph_store.ping()
            checks["neo4j"] = "ok"
        except Exception as exc:
            checks["neo4j"] = f"error: {exc}"
            checks["status"] = "degraded"

        return JSONResponse(checks)

    return app
