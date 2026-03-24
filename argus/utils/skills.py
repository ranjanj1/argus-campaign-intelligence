from __future__ import annotations

from enum import Enum


class ClientSkill(str, Enum):
    """
    Access profiles embedded as the `skill` claim in a JWT.

    Each skill controls:
      1. Which pgvector collections are searched during RAG retrieval.
      2. Which system prompt the LLM receives.

    Assign a skill when issuing tokens to users:
      - Internal analysts       → ALL_CAMPAIGNS
      - External client portal  → SINGLE_CLIENT
      - Executive / C-suite     → EXECUTIVE
      - Performance-only access → PERFORMANCE
      - Ad creative review      → CREATIVE
      - Budget / finance review → BUDGET
    """

    ALL_CAMPAIGNS = "all_campaigns"
    SINGLE_CLIENT = "single_client"
    EXECUTIVE = "executive"
    PERFORMANCE = "performance"
    CREATIVE = "creative"
    BUDGET = "budget"


# Maps each skill to the pgvector collection names it may search.
# RAG retrieval is hard-limited to these collections — no bypass possible.
SKILL_COLLECTIONS: dict[ClientSkill, list[str]] = {
    ClientSkill.ALL_CAMPAIGNS: [
        "campaign_performance",
        "ad_copy_library",
        "audience_segments",
        "client_strategy_briefs",
        "monthly_reports",
        "budget_allocations",
    ],
    ClientSkill.SINGLE_CLIENT: [
        "campaign_performance",
        "ad_copy_library",
        "audience_segments",
    ],
    ClientSkill.EXECUTIVE: [
        "monthly_reports",
        "client_strategy_briefs",
        "budget_allocations",
    ],
    ClientSkill.PERFORMANCE: [
        "campaign_performance",
        "audience_segments",
    ],
    ClientSkill.CREATIVE: [
        "ad_copy_library",
        "campaign_performance",
    ],
    ClientSkill.BUDGET: [
        "budget_allocations",
        "monthly_reports",
    ],
}


def get_allowed_collections(skill: ClientSkill | str) -> list[str]:
    """Return the list of collections a given skill may search.

    Accepts either a ClientSkill enum value or a raw string claim from a JWT.
    Falls back to SINGLE_CLIENT (most restrictive) if the claim is unrecognised.
    """
    try:
        resolved = ClientSkill(skill)
    except ValueError:
        resolved = ClientSkill.SINGLE_CLIENT
    return SKILL_COLLECTIONS[resolved]
