from __future__ import annotations

"""
ARQ ingest worker — processes background ingest jobs from the Redis queue.

Enqueue a job (from the ingest router):
    await arq_pool.enqueue_job(
        "ingest_file_job",
        filename=filename,
        data=file_bytes,         # bytes
        collection=collection,
        client_id=client_id,
        doc_id=doc_id,
    )

Run the worker:
    poetry run python -m arq argus.components.ingest.ingest_worker.WorkerSettings
"""

import logging

from argus.components.ingest.ingest_component import IngestComponent
from argus.di import get_injector
from argus.settings.settings_loader import load_settings

logger = logging.getLogger(__name__)


# ── Job function ──────────────────────────────────────────────────────────────

async def ingest_file_job(
    ctx: dict,
    filename: str,
    data: bytes,
    collection: str,
    client_id: str,
    doc_id: str | None = None,
) -> dict:
    """
    ARQ job: ingest a single file.

    The job receives raw bytes (serialised by ARQ via msgpack) so it works
    regardless of where the file was uploaded.

    Returns a dict summary that ARQ stores as the job result.
    """
    ingest: IngestComponent = ctx["ingest"]
    logger.info(
        "ARQ ingest_file_job start: file=%s collection=%s client=%s",
        filename, collection, client_id,
    )

    result = await ingest.ingest_bytes(
        data=data,
        filename=filename,
        collection=collection,
        client_id=client_id,
        doc_id=doc_id,
    )

    summary = {
        "doc_id": result.doc_id,
        "collection": result.collection,
        "source_file": result.source_file,
        "chunk_count": result.chunk_count,
        "entity_count": result.entity_count,
        "error": result.error,
        "status": "error" if result.error else "ok",
    }
    if result.error:
        logger.error("ARQ ingest_file_job FAILED: %s", result.error)
    else:
        logger.info(
            "ARQ ingest_file_job OK: doc=%s chunks=%d entities=%d",
            result.doc_id, result.chunk_count, result.entity_count,
        )
    return summary


# ── Worker lifecycle hooks ────────────────────────────────────────────────────

async def startup(ctx: dict) -> None:
    """
    Initialise shared components once per worker process.
    Stored in ctx so job functions can access them without re-initialising.
    """
    injector = get_injector()
    ctx["ingest"] = injector.get(IngestComponent)
    logger.info("ARQ worker startup complete")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker shutting down")


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    """
    ARQ WorkerSettings — referenced by `arq argus.components.ingest.ingest_worker.WorkerSettings`
    """
    functions = [ingest_file_job]
    on_startup = startup
    on_shutdown = shutdown

    # Read Redis URL from settings
    @staticmethod
    def _redis_url() -> str:
        return load_settings().redis.url

    redis_settings = None   # populated below

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)


# Resolve redis_settings at import time (ARQ reads it as a class attribute)
try:
    from arq.connections import RedisSettings as _ARQRedisSettings
    _cfg = load_settings().redis
    WorkerSettings.redis_settings = _ARQRedisSettings(
        host=_cfg.host,
        port=_cfg.port,
    )
except Exception:
    pass  # will fail at worker startup with a clear error if Redis is unreachable
