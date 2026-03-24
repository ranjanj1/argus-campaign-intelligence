"""
Download and normalise real Kaggle datasets for Argus seed data.

Requires Kaggle API credentials: either ~/.kaggle/kaggle.json
or KAGGLE_USERNAME + KAGGLE_KEY environment variables (loaded from .env).

Usage:
    poetry run download-kaggle --verbose
    poetry run download-kaggle --sling-only   # no Kaggle key needed
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

import click
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console

console = Console()

SLING_URL = "https://api.slingacademy.com/v1/sample-data/files/marketing-campaigns.csv"

# Kaggle dataset slugs
KAGGLE_DATASETS = {
    "campaign_performance": "manishabhatt22/marketing-campaign-performance-dataset",
    "social_ads": "jsonk11/social-media-advertising-dataset",
}

# Column mappings: Kaggle column name → Argus schema column name
CAMPAIGN_PERF_COLUMNS = {
    # manishabhatt22 dataset columns (approximate — actual names normalised below)
    "campaign_id": "source_campaign_id",
    "campaign_name": "campaign_name",
    "channel_type": "channel",
    "target_audience": "target_audience",
    "duration": "duration_days",
    "channels_used": "channels_used",
    "conversion_rate": "conversion_rate",
    "acquisition_cost": "cpa",
    "roi": "roas_proxy",
    "location": "location",
    "language": "language",
    "clicks": "clicks",
    "impressions": "impressions",
    "engagement_score": "engagement_score",
    "customer_segment": "audience_segment",
    "company": "company_tag",
}

SOCIAL_ADS_COLUMNS = {
    "age": "age_range",
    "gender": "gender",
    "interests": "interests",
    "income": "income_bracket",
    "education": "education",
    "platform": "platform",
    "ad_position": "ad_position",
    "browsing_history": "browsing_history",
    "time_of_day": "time_of_day",
    "device_type": "device_type",
    "ad_spend": "spend",
    "click_through_rate": "ctr",
    "conversion_rate": "conversion_rate",
    "ad_click_through_rate": "ctr_alt",
}


def _try_kaggle_download(slug: str, dest_dir: Path) -> Path | None:
    """Download a Kaggle dataset zip and extract to dest_dir. Returns extracted path or None."""
    try:
        import kaggle
        # kaggle >= 1.6 exposes the API directly on the module
        api = kaggle.api
        api.authenticate()
        console.print(f"  Downloading kaggle dataset: {slug}")
        api.dataset_download_files(slug, path=str(dest_dir), unzip=True, quiet=False)
        return dest_dir
    except Exception as e:
        console.print(f"  [yellow]Kaggle download failed ({e})[/yellow]")
        return None


def _download_sling(dest_dir: Path) -> Path:
    """Download Sling Academy CSV — no login required."""
    import urllib.request
    out = dest_dir / "sling_marketing_campaigns.csv"
    if out.exists():
        console.print(f"  [dim]Sling CSV already exists, skipping download[/dim]")
        return out
    console.print(f"  Downloading Sling Academy marketing campaigns CSV...")
    urllib.request.urlretrieve(SLING_URL, out)
    console.print(f"  [green]✓[/green] sling_marketing_campaigns.csv")
    return out


def _normalise_campaign_performance(raw_dir: Path, out_dir: Path) -> bool:
    """Find and normalise the Kaggle campaign performance CSV."""
    EXCLUDE = {"sling_marketing_campaigns.csv", "campaign_performance_raw.csv",
               "social_ads_raw.csv", "Social_Media_Advertising.csv"}
    # Prefer files with "campaign" or "marketing" in the name, exclude social ads
    kaggle_candidates = sorted(
        [f for f in raw_dir.glob("*.csv")
         if f.name not in EXCLUDE
         and "social" not in f.name.lower()
         and "advertis" not in f.name.lower()],
        key=lambda f: (
            0 if ("campaign" in f.name.lower() or "marketing" in f.name.lower()) else 1
        )
    )
    sling_fallback = [raw_dir / "sling_marketing_campaigns.csv"]
    candidates = kaggle_candidates + sling_fallback

    df = None
    for cand in candidates:
        try:
            tmp = pd.read_csv(cand, nrows=5)
            # The manishabhatt22 dataset has 'Conversion Rate' and 'ROI' columns
            cols_lower = [c.lower().replace(" ", "_") for c in tmp.columns]
            if "conversion_rate" in cols_lower or "roi" in cols_lower:
                df = pd.read_csv(cand)
                console.print(f"  Found campaign performance data: {cand.name} ({len(df)} rows)")
                break
        except Exception:
            continue

    if df is None:
        console.print("  [yellow]No campaign performance CSV found — using Sling fallback[/yellow]")
        sling = out_dir / "sling_marketing_campaigns.csv"
        if sling.exists():
            df = pd.read_csv(sling)
        else:
            return False

    # Normalise column names (lowercase + underscores)
    df.columns = [c.lower().strip().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Ensure key columns exist with sensible defaults
    if "channel" not in df.columns:
        for alias in ["channel_type", "channels_used", "platform"]:
            if alias in df.columns:
                df["channel"] = df[alias]
                break
        else:
            df["channel"] = "unknown"

    if "impressions" not in df.columns:
        df["impressions"] = (df.get("clicks", pd.Series([1000] * len(df))) * 25).astype(int)

    if "clicks" not in df.columns:
        df["clicks"] = (df.get("impressions", pd.Series([25000] * len(df))) * 0.02).astype(int)

    if "spend" not in df.columns:
        for alias in ["acquisition_cost", "ad_spend", "budget", "cost"]:
            if alias in df.columns:
                df["spend"] = pd.to_numeric(df[alias], errors="coerce").fillna(500)
                break
        else:
            df["spend"] = 500.0

    if "revenue" not in df.columns:
        # Derive from ROI if available: revenue = spend * (1 + ROI/100) or spend * roas_proxy
        for alias in ["roi", "roas_proxy", "revenue_generated"]:
            if alias in df.columns:
                try:
                    roi = pd.to_numeric(df[alias], errors="coerce").fillna(3.0)
                    if roi.median() > 10:  # likely percentage
                        df["revenue"] = df["spend"] * (1 + roi / 100)
                    else:
                        df["revenue"] = df["spend"] * roi
                    break
                except Exception:
                    continue
        else:
            df["revenue"] = df["spend"] * 3.5

    # Ensure numeric
    for col in ["impressions", "clicks", "spend", "revenue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Derive ROAS
    df["roas"] = (df["revenue"] / df["spend"].replace(0, 1)).round(2)
    df["ctr"] = (df["clicks"] / df["impressions"].replace(0, 1)).round(4)

    out_path = out_dir / "campaign_performance_raw.csv"
    df.to_csv(out_path, index=False)
    console.print(f"  [green]✓[/green] campaign_performance_raw.csv ({len(df)} rows, {len(df.columns)} cols)")
    return True


def _normalise_social_ads(raw_dir: Path, out_dir: Path) -> bool:
    """Find and normalise the social ads / audience CSV."""
    EXCLUDE = {"sling_marketing_campaigns.csv", "campaign_performance_raw.csv", "social_ads_raw.csv"}
    # Prefer files with "social", "advertising", or "audience" in name
    candidates = sorted(
        [f for f in raw_dir.glob("*.csv") if f.name not in EXCLUDE],
        key=lambda f: (
            0 if any(kw in f.name.lower() for kw in ["social", "advertis", "audience"]) else 1
        )
    )

    df = None
    for cand in candidates:
        if "campaign_performance_raw" in cand.name:
            continue
        try:
            tmp = pd.read_csv(cand, nrows=5)
            cols_lower = [c.lower() for c in tmp.columns]
            if any(k in cols_lower for k in ["age", "gender", "platform", "interest"]):
                df = pd.read_csv(cand)
                console.print(f"  Found social ads data: {cand.name} ({len(df)} rows)")
                break
        except Exception:
            continue

    if df is None:
        console.print("  [yellow]No social ads CSV found — audience segments will be Faker-generated[/yellow]")
        return False

    df.columns = [c.lower().strip().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Ensure key columns
    if "platform" not in df.columns:
        df["platform"] = "meta"
    if "ctr" not in df.columns:
        for alias in ["click_through_rate", "ad_click_through_rate"]:
            if alias in df.columns:
                df["ctr"] = pd.to_numeric(df[alias], errors="coerce").fillna(0.02)
                break
        else:
            df["ctr"] = 0.02
    if "conversion_rate" not in df.columns:
        df["conversion_rate"] = 0.02
    if "spend" not in df.columns:
        df["spend"] = 500.0

    out_path = out_dir / "social_ads_raw.csv"
    df.to_csv(out_path, index=False)
    console.print(f"  [green]✓[/green] social_ads_raw.csv ({len(df)} rows, {len(df.columns)} cols)")
    return True


@click.command()
@click.option("--output-dir", default="data/raw", show_default=True, type=click.Path())
@click.option("--sling-only", is_flag=True, default=False,
              help="Download only the no-login Sling Academy CSV (no Kaggle key required).")
@click.option("-v", "--verbose", is_flag=True, default=False)
def cli(output_dir: str, sling_only: bool, verbose: bool) -> None:
    """Download and normalise real marketing datasets into data/raw/."""
    load_dotenv()

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold blue]Argus Kaggle Downloader[/bold blue]")
    console.print(f"  Output: {out}\n")

    # Always download Sling (no login, always works)
    _download_sling(out)

    if not sling_only:
        # Set Kaggle credentials from env vars if present
        if os.environ.get("KAGGLE_USERNAME"):
            os.environ["KAGGLE_USERNAME"] = os.environ["KAGGLE_USERNAME"]
        if os.environ.get("KAGGLE_KEY"):
            os.environ["KAGGLE_KEY"] = os.environ["KAGGLE_KEY"]

        for name, slug in KAGGLE_DATASETS.items():
            console.print(f"\nDataset: {name} ({slug})")
            _try_kaggle_download(slug, out)
    else:
        console.print("\n[dim]Skipping Kaggle downloads (--sling-only)[/dim]")

    console.print("\n[bold]Normalising raw data...[/bold]")
    _normalise_campaign_performance(out, out)
    _normalise_social_ads(out, out)

    console.print(f"\n[bold green]Done! Raw data saved to {out}[/bold green]")
    console.print("\nNext step:")
    console.print("  poetry run seed --verbose")


if __name__ == "__main__":
    cli()
