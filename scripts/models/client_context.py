from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class VerticalConfig:
    industry: str
    roas_range: tuple[float, float]
    ctr_range: tuple[float, float]
    cpa_range: tuple[float, float]
    conversion_rate_range: tuple[float, float]
    cpm_range: tuple[float, float]
    monthly_budget_range: tuple[float, float]
    primary_channels: list[str]
    tone_keywords: list[str]
    competitors: list[str]
    business_objectives: list[str]


@dataclass
class SegmentSeed:
    segment_id: str
    segment_name: str
    age_range: str
    gender: str
    interests: list[str]
    platform: str
    size: int
    cpm: float
    # computed after campaign assignment
    total_spend: float = 0.0
    avg_ctr: float = 0.0
    avg_conversion_rate: float = 0.0


@dataclass
class CampaignSeed:
    campaign_id: str
    name: str
    channel: str
    status: str           # "active" | "paused" | "completed"
    start_date: date
    end_date: date
    audience_segment_id: str
    total_budget: float
    # metric chain — computed once in profile builder
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0


@dataclass
class ClientProfile:
    client_id: str
    company_name: str
    industry: str
    vertical_config: VerticalConfig
    campaigns: list[CampaignSeed] = field(default_factory=list)
    segments: list[SegmentSeed] = field(default_factory=list)
    report_month: str = "Q1 2025"


# Pre-defined client specs
CLIENT_SPECS: dict[str, dict] = {
    "acme_corp": {
        "company_name": "Acme Corporation",
        "industry": "retail",
        "monthly_budget": 120_000,
    },
    "techflow": {
        "company_name": "TechFlow Inc.",
        "industry": "saas",
        "monthly_budget": 45_000,
    },
    "greenleaf": {
        "company_name": "GreenLeaf Commerce",
        "industry": "ecommerce",
        "monthly_budget": 80_000,
    },
    "northstar": {
        "company_name": "NorthStar Financial",
        "industry": "finance",
        "monthly_budget": 200_000,
    },
}
