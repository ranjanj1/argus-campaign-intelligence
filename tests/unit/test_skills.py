from __future__ import annotations

import pytest

from argus.utils.skills import ClientSkill, SKILL_COLLECTIONS, get_allowed_collections


def test_all_skills_have_collections():
    for skill in ClientSkill:
        assert skill in SKILL_COLLECTIONS, f"{skill} missing from SKILL_COLLECTIONS"
        assert len(SKILL_COLLECTIONS[skill]) > 0


def test_all_campaigns_has_all_six_collections():
    cols = get_allowed_collections(ClientSkill.ALL_CAMPAIGNS)
    assert len(cols) == 6


def test_most_restrictive_skills_are_subsets_of_all_campaigns():
    all_cols = set(get_allowed_collections(ClientSkill.ALL_CAMPAIGNS))
    for skill in ClientSkill:
        assert set(get_allowed_collections(skill)).issubset(all_cols), (
            f"{skill} references unknown collection"
        )


def test_get_allowed_collections_accepts_string():
    cols = get_allowed_collections("executive")
    assert "monthly_reports" in cols
    assert "campaign_performance" not in cols


def test_unknown_skill_falls_back_to_single_client():
    cols = get_allowed_collections("nonexistent_skill")
    assert cols == get_allowed_collections(ClientSkill.SINGLE_CLIENT)


def test_single_client_cannot_see_strategy_briefs():
    cols = get_allowed_collections(ClientSkill.SINGLE_CLIENT)
    assert "client_strategy_briefs" not in cols
    assert "monthly_reports" not in cols
