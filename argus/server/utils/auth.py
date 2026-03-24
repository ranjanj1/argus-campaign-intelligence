from __future__ import annotations

"""
JWT authentication dependency for FastAPI route handlers.

Token format (HS256, symmetric):
  {
    "sub":              "user-123",          # user ID
    "skill":            "single_client",     # ClientSkill value
    "client_id":        "acme_corp",         # which client's data this user owns
    "exp":              1234567890           # expiry (standard JWT claim)
  }

When auth is disabled (develop profile), every request is assigned the
default_skill and default_client_id from settings — no token needed.

Usage in a route:
    @router.post("/v1/chat")
    async def chat(payload: dict = Depends(require_auth)):
        skill = payload["skill"]
        client_id = payload["client_id"]
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from argus.di import get_settings
from argus.utils.skills import ClientSkill, get_allowed_collections

_bearer = HTTPBearer(auto_error=False)


def _decode_token(token: str, settings) -> dict:
    """Decode and validate a JWT. Raises HTTPException on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret,
            algorithms=[settings.auth.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )
    return payload


def _build_identity(raw_skill: str, client_id: str) -> dict:
    """Resolve skill + allowed collections from raw JWT claims."""
    skill = ClientSkill(raw_skill) if raw_skill in ClientSkill._value2member_map_ else ClientSkill.SINGLE_CLIENT
    return {
        "skill": skill,
        "client_id": client_id,
        "allowed_collections": get_allowed_collections(skill),
    }


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — resolves to an identity dict:
        {
            "skill":               ClientSkill,
            "client_id":           str,
            "allowed_collections": list[str],
        }

    When auth is disabled, returns the default identity from settings.
    When auth is enabled, validates the Bearer token and extracts claims.
    """
    settings = get_settings()

    if not settings.auth.enabled:
        return _build_identity(
            settings.auth.default_skill,
            settings.auth.default_client_id,
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials, settings)

    raw_skill = payload.get("skill", settings.auth.default_skill)
    client_id = payload.get("client_id", settings.auth.default_client_id)

    return _build_identity(raw_skill, client_id)


def create_token(
    skill: ClientSkill | str,
    client_id: str,
    subject: str = "user",
    expires_in_hours: int = 24,
) -> str:
    """
    Generate a signed JWT for development / testing.

    Example:
        token = create_token(ClientSkill.ALL_CAMPAIGNS, "acme_corp")
        # Use as:  Authorization: Bearer <token>
    """
    import time

    settings = get_settings()
    skill_value = skill.value if isinstance(skill, ClientSkill) else skill

    payload = {
        "sub": subject,
        "skill": skill_value,
        "client_id": client_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_hours * 3600,
    }
    return jwt.encode(
        payload,
        settings.auth.jwt_secret,
        algorithm=settings.auth.jwt_algorithm,
    )
