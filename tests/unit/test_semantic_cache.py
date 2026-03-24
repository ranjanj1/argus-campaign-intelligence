"""Unit tests for SemanticCache — all external I/O is mocked."""
from __future__ import annotations

import json
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.components.cache.semantic_cache import SemanticCache, _cosine_similarity
from argus.settings.settings import Settings


# ── helpers ──────────────────────────────────────────────────────────────────

def _unit_vec(dim: int = 4, idx: int = 0) -> list[float]:
    """One-hot vector of given dimension."""
    v = [0.0] * dim
    v[idx] = 1.0
    return v


def _make_cache(threshold: float = 0.92) -> tuple[SemanticCache, MagicMock, MagicMock]:
    """Return (cache, mock_redis, mock_embedder) with threshold applied."""
    settings = Settings()
    settings.redis.cache_similarity_threshold = threshold

    mock_embedder = MagicMock()
    cache = SemanticCache.__new__(SemanticCache)
    cache._cfg = settings.redis
    cache._embedder = mock_embedder

    # Use MagicMock (not AsyncMock) so scan_iter / pipeline are not auto-awaited.
    mock_redis = MagicMock()
    cache._redis = mock_redis
    return cache, mock_redis, mock_embedder


# ── _cosine_similarity ────────────────────────────────────────────────────────

def test_cosine_identical():
    v = [1.0, 0.0, 0.0]
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_zero_vector():
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ── SemanticCache.get ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_cache_hit():
    cache, mock_redis, mock_embedder = _make_cache(threshold=0.90)

    query_vec = _unit_vec(4, 0)
    mock_embedder.embed = AsyncMock(return_value=query_vec)

    cached_response = {"answer": "cached answer", "sources": []}
    entry = {
        "embedding": json.dumps(query_vec),   # identical → sim = 1.0
        "response": json.dumps(cached_response),
        "query": "original query",
    }
    mock_redis.scan_iter = MagicMock(return_value=_async_iter(["argus:cache:all_campaigns:acme:abc123"]))
    mock_redis.hgetall = AsyncMock(return_value=entry)

    result = await cache.get("any query", "all_campaigns", "acme")
    assert result == cached_response


@pytest.mark.asyncio
async def test_get_cache_miss_low_similarity():
    cache, mock_redis, mock_embedder = _make_cache(threshold=0.92)

    mock_embedder.embed = AsyncMock(return_value=_unit_vec(4, 0))

    orthogonal_vec = _unit_vec(4, 1)   # sim = 0.0
    entry = {
        "embedding": json.dumps(orthogonal_vec),
        "response": json.dumps({"answer": "stale"}),
        "query": "different query",
    }
    mock_redis.scan_iter = MagicMock(return_value=_async_iter(["argus:cache:all_campaigns:acme:xyz"]))
    mock_redis.hgetall = AsyncMock(return_value=entry)

    result = await cache.get("new query", "all_campaigns", "acme")
    assert result is None


@pytest.mark.asyncio
async def test_get_empty_cache():
    cache, mock_redis, mock_embedder = _make_cache()
    mock_embedder.embed = AsyncMock(return_value=_unit_vec(4, 0))
    mock_redis.scan_iter = MagicMock(return_value=_async_iter([]))

    result = await cache.get("q", "all_campaigns", "acme")
    assert result is None


# ── SemanticCache.set ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_writes_hash_with_ttl():
    cache, mock_redis, mock_embedder = _make_cache()

    vec = _unit_vec(4, 2)
    mock_embedder.embed = AsyncMock(return_value=vec)

    # pipeline() is synchronous; only execute() is async
    pipe_mock = MagicMock()
    pipe_mock.execute = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=pipe_mock)

    response = {"answer": "hello", "sources": []}
    await cache.set("test query", "performance", "techflow", response)

    pipe_mock.hset.assert_called_once()
    call_kwargs = pipe_mock.hset.call_args.kwargs
    mapping = call_kwargs["mapping"]
    assert json.loads(mapping["embedding"]) == vec
    assert json.loads(mapping["response"]) == response
    assert mapping["query"] == "test query"

    # expire is called with (key, ttl); key is a uuid string we don't control
    expire_args = pipe_mock.expire.call_args.args
    assert expire_args[1] == cache._cfg.cache_ttl
    pipe_mock.execute.assert_awaited_once()


# ── SemanticCache.invalidate ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalidate_deletes_matching_keys():
    cache, mock_redis, mock_embedder = _make_cache()

    keys = [f"argus:cache:budget:acme:{i}" for i in range(3)]
    mock_redis.scan_iter = MagicMock(return_value=_async_iter(keys))
    mock_redis.delete = AsyncMock()

    count = await cache.invalidate("budget", "acme")

    assert count == 3
    mock_redis.delete.assert_awaited_once_with(*keys)


@pytest.mark.asyncio
async def test_invalidate_no_keys():
    cache, mock_redis, mock_embedder = _make_cache()
    mock_redis.scan_iter = MagicMock(return_value=_async_iter([]))
    mock_redis.delete = AsyncMock()

    count = await cache.invalidate("budget", "acme")
    assert count == 0
    mock_redis.delete.assert_not_awaited()


# ── helpers ───────────────────────────────────────────────────────────────────

async def _async_iter(items):
    for item in items:
        yield item
