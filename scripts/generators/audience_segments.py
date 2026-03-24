from __future__ import annotations

import math

import pandas as pd

from scripts.generators.base import (
    SEGMENT_POOLS,
    VERTICAL_CONFIGS,
    make_segment_id,
    rand_float,
    rand_int,
    rand_sample,
)
from scripts.models.client_context import ClientProfile, SegmentSeed


def build_segments(client_id: str, industry: str) -> list[SegmentSeed]:
    """Generate 10 audience segments for a client."""
    config = VERTICAL_CONFIGS[industry]
    pool = SEGMENT_POOLS[industry]
    prefix = client_id[:3]

    segments: list[SegmentSeed] = []
    for i, seg_data in enumerate(pool[:10]):
        cpm = rand_float(*config.cpm_range)
        # Audience size: log-normal distribution between 50K and 5M
        log_size = rand_float(math.log(50_000), math.log(5_000_000))
        size = int(math.exp(log_size))

        segments.append(SegmentSeed(
            segment_id=make_segment_id(prefix, i + 1),
            segment_name=seg_data["name"],
            age_range=seg_data["age"],
            gender=seg_data["gender"],
            interests=seg_data["interests"],
            platform=seg_data["platform"],
            size=size,
            cpm=round(cpm, 2),
        ))
    return segments


def generate_audience_segments_df(profile: ClientProfile) -> pd.DataFrame:
    """Return DataFrame ready to write as audience_segments.csv."""
    rows = []
    for seg in profile.segments:
        rows.append({
            "segment_id": seg.segment_id,
            "segment_name": seg.segment_name,
            "age_range": seg.age_range,
            "gender": seg.gender,
            "interests": ", ".join(seg.interests),
            "platform": seg.platform,
            "audience_size": seg.size,
            "cpm": round(seg.cpm, 2),
            "total_spend": round(seg.total_spend, 2),
            "avg_ctr": round(seg.avg_ctr, 4),
            "avg_conversion_rate": round(seg.avg_conversion_rate, 4),
            "client_id": profile.client_id,
        })
    return pd.DataFrame(rows)
