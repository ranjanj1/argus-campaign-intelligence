from __future__ import annotations

import time

import pytest
import jwt

from argus.utils.skills import ClientSkill
from argus.server.utils.auth import create_token, _decode_token, _build_identity
from argus.settings.settings import AuthSettings


# ── Helpers ───────────────────────────────────────────────────────────────────

_TEST_SECRET = "test-secret-key-that-is-long-enough-for-hs256"

class _FakeSettings:
    auth = AuthSettings(
        enabled=True,
        jwt_secret=_TEST_SECRET,
        jwt_algorithm="HS256",
    )


def _make_raw_token(payload: dict, secret: str = _TEST_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_token_decodes_correctly():
    import unittest.mock as mock

    with mock.patch("argus.server.utils.auth.get_settings", return_value=_FakeSettings()):
        token = create_token(ClientSkill.SINGLE_CLIENT, "acme_corp", subject="user-1")

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    assert payload["skill"] == "single_client"
    assert payload["client_id"] == "acme_corp"
    assert payload["sub"] == "user-1"


def test_decode_token_valid():
    raw = _make_raw_token({"sub": "u1", "skill": "executive", "client_id": "northstar",
                           "exp": int(time.time()) + 3600})
    result = _decode_token(raw, _FakeSettings())
    assert result["skill"] == "executive"


def test_decode_token_expired_raises():
    from fastapi import HTTPException
    raw = _make_raw_token({"sub": "u1", "exp": int(time.time()) - 10})
    with pytest.raises(HTTPException) as exc_info:
        _decode_token(raw, _FakeSettings())
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_decode_token_bad_signature_raises():
    from fastapi import HTTPException
    raw = _make_raw_token({"sub": "u1", "exp": int(time.time()) + 3600},
                          secret="wrong-secret-key-that-is-long-enough-for-hs256")
    with pytest.raises(HTTPException) as exc_info:
        _decode_token(raw, _FakeSettings())
    assert exc_info.value.status_code == 401


def test_build_identity_valid_skill():
    identity = _build_identity("performance", "techflow")
    assert identity["skill"] == ClientSkill.PERFORMANCE
    assert identity["client_id"] == "techflow"
    assert "campaign_performance" in identity["allowed_collections"]


def test_build_identity_unknown_skill_falls_back():
    identity = _build_identity("garbage_skill", "someone")
    assert identity["skill"] == ClientSkill.SINGLE_CLIENT
