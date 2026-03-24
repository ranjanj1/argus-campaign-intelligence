from __future__ import annotations

import random
from datetime import timedelta

import pandas as pd

from scripts.generators.base import (
    VERTICAL_CONFIGS,
    generate_campaign_name,
    make_campaign_id,
    rand_float,
    rand_int,
    rand_choice,
    weighted_date_range,
    clamp,
)
from scripts.models.client_context import CampaignSeed, ClientProfile, SegmentSeed


def build_campaigns(
    client_id: str,
    industry: str,
    segments: list[SegmentSeed],
    n: int = 50,
) -> list[CampaignSeed]:
    """
    Generate n CampaignSeed objects with the full metric chain computed once.
    Writes back aggregated spend/CTR to segments so audience_segments.csv stays coherent.
    """
    config = VERTICAL_CONFIGS[industry]
    prefix = client_id[:4]

    # Status distribution: 60% active, 25% completed, 15% paused
    statuses = (["active"] * 30) + (["completed"] * 15) + (["paused"] * (n - 45))
    random.shuffle(statuses)

    campaigns: list[CampaignSeed] = []
    seg_spend_acc: dict[str, float] = {s.segment_id: 0.0 for s in segments}
    seg_ctr_acc: dict[str, list[float]] = {s.segment_id: [] for s in segments}
    seg_cvr_acc: dict[str, list[float]] = {s.segment_id: [] for s in segments}

    for i in range(n):
        status = statuses[i]
        segment = segments[i % len(segments)]
        channel = rand_choice(config.primary_channels)

        start, end = weighted_date_range(2024, status)

        # Budget: fraction of client monthly budget
        campaign_budget = rand_float(
            config.monthly_budget_range[0] * 0.05,
            config.monthly_budget_range[1] * 0.3,
        )

        # Metric derivation chain — never re-randomised downstream
        cpm = rand_float(*config.cpm_range)
        impressions = int(campaign_budget / (cpm / 1000))

        ctr = rand_float(*config.ctr_range)
        clicks = int(impressions * ctr)

        cvr = rand_float(*config.conversion_rate_range)
        conversions = int(clicks * cvr)

        # Actual spend: impressions × CPM (slightly under budget)
        spend = clamp(impressions * (cpm / 1000), campaign_budget * 0.7, campaign_budget)

        roas = rand_float(*config.roas_range)
        revenue = spend * roas

        name = generate_campaign_name(channel, industry, segment.segment_name)

        camp = CampaignSeed(
            campaign_id=make_campaign_id(prefix, i + 1),
            name=name,
            channel=channel,
            status=status,
            start_date=start,
            end_date=end,
            audience_segment_id=segment.segment_id,
            total_budget=round(campaign_budget, 2),
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=round(spend, 2),
            revenue=round(revenue, 2),
        )
        campaigns.append(camp)

        # Accumulate for segment roll-up
        seg_spend_acc[segment.segment_id] += spend
        seg_ctr_acc[segment.segment_id].append(ctr)
        seg_cvr_acc[segment.segment_id].append(cvr)

    # Write back aggregated metrics to segments
    for seg in segments:
        seg.total_spend = round(seg_spend_acc[seg.segment_id], 2)
        ctrs = seg_ctr_acc[seg.segment_id]
        cvrs = seg_cvr_acc[seg.segment_id]
        seg.avg_ctr = round(sum(ctrs) / len(ctrs), 4) if ctrs else 0.0
        seg.avg_conversion_rate = round(sum(cvrs) / len(cvrs), 4) if cvrs else 0.0

    return campaigns


def generate_campaign_performance_df(profile: ClientProfile) -> pd.DataFrame:
    """Return DataFrame ready to write as campaign_performance.csv."""
    rows = []
    for c in profile.campaigns:
        clicks = max(c.clicks, 1)
        impressions = max(c.impressions, 1)
        ctr = round(clicks / impressions, 4)
        cvr = round(c.conversions / clicks, 4) if clicks else 0.0
        cpa = round(c.spend / c.conversions, 2) if c.conversions else None
        roas = round(c.revenue / c.spend, 2) if c.spend else 0.0

        rows.append({
            "campaign_id": c.campaign_id,
            "campaign_name": c.name,
            "client_id": profile.client_id,
            "channel": c.channel,
            "status": c.status,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "audience_segment_id": c.audience_segment_id,
            "total_budget": c.total_budget,
            "impressions": c.impressions,
            "clicks": c.clicks,
            "conversions": c.conversions,
            "spend": c.spend,
            "revenue": c.revenue,
            "ctr": ctr,
            "conversion_rate": cvr,
            "cpa": cpa,
            "roas": roas,
        })
    return pd.DataFrame(rows)
