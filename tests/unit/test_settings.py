"""Week 1 smoke tests — settings load and DI resolves."""
import os

import pytest

from argus.settings.settings_loader import load_settings
from argus.settings.settings import Settings


def test_settings_load_defaults():
    """Settings load from settings.yaml with all defaults present."""
    s = load_settings()
    assert isinstance(s, Settings)
    assert s.llm.model == "gpt-4o"
    assert s.embedding.dimensions == 768
    assert len(s.pgvector.tables) == 6
    assert s.neo4j.uri.startswith("bolt://")
    assert s.redis.cache_similarity_threshold == 0.92


def test_settings_develop_profile(monkeypatch):
    """develop profile disables auth and raises rate limits."""
    monkeypatch.setenv("ARGUS_PROFILES", "develop")
    s = load_settings()
    assert s.auth.enabled is False
    assert s.rate_limit.requests_per_minute == 1000


def test_env_var_substitution(monkeypatch):
    """${ENV_VAR:default} substitution works correctly."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "supersecret")
    monkeypatch.delenv("ARGUS_PROFILES", raising=False)
    s = load_settings()
    assert s.pgvector.password == "supersecret"


def test_env_var_default_when_not_set(monkeypatch):
    """Falls back to default when env var is absent."""
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("ARGUS_PROFILES", raising=False)
    s = load_settings()
    assert s.pgvector.password == "argus"


def test_di_resolves_settings():
    """DI container resolves Settings singleton."""
    from argus.di import get_injector
    injector = get_injector()
    s = injector.get(Settings)
    assert isinstance(s, Settings)


def test_health_endpoint():
    """GET /health returns 200 and expected shape (DB pings are mocked)."""
    from unittest.mock import AsyncMock, patch
    from fastapi.testclient import TestClient
    from argus.main import app

    with patch(
        "argus.components.vector_store.vector_store_component.VectorStoreComponent.ping",
        new_callable=AsyncMock, return_value=True,
    ), patch(
        "argus.components.graph_store.graph_store_component.GraphStoreComponent.ping",
        new_callable=AsyncMock, return_value=True,
    ):
        client = TestClient(app)
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
