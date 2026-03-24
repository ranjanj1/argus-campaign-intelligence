from __future__ import annotations

import json
import logging
import math
import uuid
from typing import Any

import redis.asyncio as aioredis
from injector import inject, singleton

from argus.components.embedding.embedding_component import EmbeddingComponent
from argus.settings.settings import Settings

logger = logging.getLogger(__name__)

_NAMESPACE = "argus:cache"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@singleton
class SemanticCache:
    """
    Redis-backed semantic cache keyed by query embedding similarity.

    Layout:
      argus:cache:{skill}:{client_id}:{uuid}  →  Redis HASH
        embedding  : JSON float list
        response   : JSON-encoded response dict
        query      : original query string (for debugging)

    On lookup:
      1. Embed the incoming query.
      2. SCAN argus:cache:{skill}:{client_id}:* to fetch candidates.
      3. Compute cosine similarity; return the best hit if >= threshold.

    On store:
      Write a new HASH with TTL = cache_ttl (default 1 hour).
    """

    @inject
    def __init__(self, settings: Settings, embedder: EmbeddingComponent) -> None:
        self._cfg = settings.redis
        self._embedder = embedder
        self._redis: aioredis.Redis = aioredis.from_url(
            self._cfg.url,
            encoding="utf-8",
            decode_responses=True,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get(
        self,
        query: str,
        skill: str,
        client_id: str,
    ) -> dict[str, Any] | None:
        """
        Return a cached response dict if a semantically similar query exists,
        otherwise return None.
        """
        query_vec = await self._embedder.embed(query)
        pattern = f"{_NAMESPACE}:{skill}:{client_id}:*"

        best_sim = -1.0
        best_response: dict[str, Any] | None = None

        async for key in self._redis.scan_iter(pattern, count=200):
            try:
                entry = await self._redis.hgetall(key)
                if not entry:
                    continue
                cached_vec: list[float] = json.loads(entry["embedding"])
                sim = _cosine_similarity(query_vec, cached_vec)
                if sim > best_sim:
                    best_sim = sim
                    best_response = json.loads(entry["response"])
            except Exception:
                logger.debug("Skipping malformed cache entry: %s", key)

        if best_sim >= self._cfg.cache_similarity_threshold and best_response is not None:
            logger.info(
                "Cache HIT  skill=%s client=%s sim=%.4f", skill, client_id, best_sim
            )
            return best_response

        logger.debug("Cache MISS skill=%s client=%s best_sim=%.4f", skill, client_id, best_sim)
        return None

    async def set(
        self,
        query: str,
        skill: str,
        client_id: str,
        response: dict[str, Any],
    ) -> None:
        """
        Embed the query and store the response in Redis with cache_ttl expiry.
        """
        query_vec = await self._embedder.embed(query)
        key = f"{_NAMESPACE}:{skill}:{client_id}:{uuid.uuid4().hex}"

        mapping = {
            "embedding": json.dumps(query_vec),
            "response": json.dumps(response),
            "query": query,
        }
        pipe = self._redis.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, self._cfg.cache_ttl)
        await pipe.execute()

        logger.info("Cache SET  skill=%s client=%s key=%s", skill, client_id, key)

    async def invalidate(self, skill: str, client_id: str) -> int:
        """
        Delete all cache entries for a given skill + client. Returns count deleted.
        Useful after re-ingestion so stale answers don't persist.
        """
        pattern = f"{_NAMESPACE}:{skill}:{client_id}:*"
        keys = [k async for k in self._redis.scan_iter(pattern, count=200)]
        if keys:
            await self._redis.delete(*keys)
        logger.info("Cache INVALIDATED skill=%s client=%s count=%d", skill, client_id, len(keys))
        return len(keys)

    async def close(self) -> None:
        """Gracefully close the Redis connection pool."""
        await self._redis.aclose()
