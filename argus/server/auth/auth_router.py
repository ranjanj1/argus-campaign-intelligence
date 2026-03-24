from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from argus.server.utils.auth import create_token
from argus.utils.skills import ClientSkill

router = APIRouter(prefix="/v1/auth", tags=["auth"])

VALID_CLIENTS = {"acme_corp", "techflow", "greenleaf", "northstar"}


class TokenRequest(BaseModel):
    client_id: str
    skill: str = "all_campaigns"


class TokenResponse(BaseModel):
    token: str
    client_id: str
    skill: str


@router.post("/token", response_model=TokenResponse)
async def get_token(body: TokenRequest) -> TokenResponse:
    """
    Issue a signed JWT for the given client_id + skill.
    Dev-only substitute for Cognito — lets you test auth without AWS.
    """
    if body.client_id not in VALID_CLIENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown client_id '{body.client_id}'. Valid: {sorted(VALID_CLIENTS)}",
        )
    if body.skill not in ClientSkill._value2member_map_:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown skill '{body.skill}'. Valid: {[s.value for s in ClientSkill]}",
        )

    token = create_token(skill=body.skill, client_id=body.client_id)
    return TokenResponse(token=token, client_id=body.client_id, skill=body.skill)
