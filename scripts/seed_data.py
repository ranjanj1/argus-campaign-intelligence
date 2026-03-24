"""
Argus seed data generator — creates a coherent fake "agency world" for testing.

Usage:
    poetry run seed --verbose                    # all 4 clients, full output
    poetry run seed --no-docs --verbose          # CSV/XLSX only, skip PDF/DOCX
    poetry run seed --clients acme_corp,techflow
    poetry run seed --sling-only                 # use only the no-auth Sling CSV

Prereq: run `poetry run download-kaggle` first to populate data/raw/.
If data/raw/ is empty, Faker-based synthetic data is used as fallback.
"""
from __future__ import annotations

from pathlib import Path

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from scripts.generators.base import set_seed, VERTICAL_CONFIGS
from scripts.generators.audience_segments import build_segments, generate_audience_segments_df
from scripts.generators.campaign_performance import build_campaigns, generate_campaign_performance_df
from scripts.generators.ad_copy_library import generate_ad_copy_library_df
from scripts.generators.budget_allocation import generate_budget_allocation_xlsx
from scripts.generators.monthly_report import generate_monthly_report_pdf
from scripts.generators.strategy_brief import generate_strategy_brief_docx
from scripts.models.client_context import ClientProfile, CLIENT_SPECS

console = Console()
ALL_CLIENTS = list(CLIENT_SPECS.keys())


# ---------------------------------------------------------------------------
# Real-data slicing: read from data/raw/ and assign rows to clients
# ---------------------------------------------------------------------------

def _load_raw_campaigns(raw_dir: Path) -> pd.DataFrame | None:
    path = raw_dir / "campaign_performance_raw.csv"
    if path.exists():
        df = pd.read_csv(path)
        console.print(f"  [dim]Using real Kaggle campaign data ({len(df)} rows)[/dim]")
        return df
    return None


def _load_raw_social_ads(raw_dir: Path) -> pd.DataFrame | None:
    path = raw_dir / "social_ads_raw.csv"
    if path.exists():
        df = pd.read_csv(path)
        console.print(f"  [dim]Using real Kaggle social ads data ({len(df)} rows)[/dim]")
        return df
    return None


def _slice_campaigns_from_real(
    df: pd.DataFrame,
    client_id: str,
    industry: str,
    segments,
    n: int = 50,
) -> list:
    """
    Slice n rows from the real dataset and coerce them into CampaignSeed objects.
    Rows are selected deterministically by client index so each client gets different rows.
    """
    from scripts.models.client_context import CampaignSeed
    from scripts.generators.base import make_campaign_id, rand_choice, rand_float, VERTICAL_CONFIGS
    from datetime import date, timedelta
    import random

    config = VERTICAL_CONFIGS[industry]
    client_idx = ALL_CLIENTS.index(client_id)
    chunk_size = max(n, len(df) // len(ALL_CLIENTS))
    start_row = client_idx * chunk_size
    subset = df.iloc[start_row: start_row + chunk_size].reset_index(drop=True)

    # If we don't have enough rows, sample with repetition
    if len(subset) < n:
        subset = df.sample(n=n, replace=True, random_state=client_idx).reset_index(drop=True)
    else:
        subset = subset.head(n)

    today = date(2025, 3, 21)
    statuses = (["active"] * 30) + (["completed"] * 15) + (["paused"] * 5)
    random.shuffle(statuses)

    campaigns = []
    for i, row in subset.iterrows():
        seg = segments[i % len(segments)]
        status = statuses[i % len(statuses)]

        if status == "completed":
            end = today - timedelta(days=random.randint(1, 180))
            start = end - timedelta(days=random.randint(14, 90))
        elif status == "active":
            start = today - timedelta(days=random.randint(7, 60))
            end = today + timedelta(days=random.randint(14, 90))
        else:
            start = today - timedelta(days=random.randint(30, 120))
            end = today + timedelta(days=random.randint(10, 60))

        # Pull metrics from real data where available
        channel = str(row.get("channel", rand_choice(config.primary_channels))).lower().replace(" ", "_")
        if channel not in config.primary_channels:
            channel = rand_choice(config.primary_channels)

        impressions = max(int(pd.to_numeric(row.get("impressions", 0), errors="coerce") or 0), 1000)
        clicks = max(int(pd.to_numeric(row.get("clicks", 0), errors="coerce") or 0), 10)
        clicks = min(clicks, impressions)
        spend = float(pd.to_numeric(row.get("spend", 0), errors="coerce") or rand_float(500, 5000))
        revenue = float(pd.to_numeric(row.get("revenue", 0), errors="coerce") or spend * rand_float(*config.roas_range))
        conversions = int(pd.to_numeric(row.get("conversions", 0), errors="coerce") or max(1, clicks // 20))

        camp_name = str(row.get("campaign_name", f"Campaign {i+1} — {channel.replace('_',' ').title()}"))[:80]

        campaigns.append(CampaignSeed(
            campaign_id=make_campaign_id(client_id[:4], i + 1),
            name=camp_name,
            channel=channel,
            status=status,
            start_date=start,
            end_date=end,
            audience_segment_id=seg.segment_id,
            total_budget=round(spend * 1.1, 2),
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            spend=round(spend, 2),
            revenue=round(revenue, 2),
        ))

    # Write back aggregated metrics to segments
    from collections import defaultdict
    seg_spend: dict[str, float] = defaultdict(float)
    seg_ctrs: dict[str, list[float]] = defaultdict(list)
    seg_cvrs: dict[str, list[float]] = defaultdict(list)
    for c in campaigns:
        seg_spend[c.audience_segment_id] += c.spend
        seg_ctrs[c.audience_segment_id].append(c.clicks / max(c.impressions, 1))
        seg_cvrs[c.audience_segment_id].append(c.conversions / max(c.clicks, 1))
    for seg in segments:
        seg.total_spend = round(seg_spend[seg.segment_id], 2)
        ctrs = seg_ctrs[seg.segment_id]
        cvrs = seg_cvrs[seg.segment_id]
        seg.avg_ctr = round(sum(ctrs) / len(ctrs), 4) if ctrs else 0.0
        seg.avg_conversion_rate = round(sum(cvrs) / len(cvrs), 4) if cvrs else 0.0

    return campaigns


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def build_client_profile(
    client_id: str,
    raw_campaigns: pd.DataFrame | None,
    raw_social: pd.DataFrame | None,
    report_month: str = "Q1 2025",
) -> ClientProfile:
    spec = CLIENT_SPECS[client_id]
    config = VERTICAL_CONFIGS[spec["industry"]]

    segments = build_segments(client_id, spec["industry"])

    if raw_campaigns is not None:
        campaigns = _slice_campaigns_from_real(raw_campaigns, client_id, spec["industry"], segments)
    else:
        campaigns = build_campaigns(client_id, spec["industry"], segments, n=50)

    return ClientProfile(
        client_id=client_id,
        company_name=spec["company_name"],
        industry=spec["industry"],
        vertical_config=config,
        segments=segments,
        campaigns=campaigns,
        report_month=report_month,
    )


# ---------------------------------------------------------------------------
# Per-client generation
# ---------------------------------------------------------------------------

def generate_client(
    profile: ClientProfile,
    output_dir: Path,
    no_docs: bool,
    verbose: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    def write(name: str, fn):
        try:
            fn()
            if verbose:
                console.print(f"  [green]✓[/green] {name}")
        except Exception as e:
            console.print(f"  [red]✗[/red] {name} — {e}")

    write("campaign_performance.csv", lambda: (
        generate_campaign_performance_df(profile)
        .to_csv(output_dir / "campaign_performance.csv", index=False)
    ))
    write("audience_segments.csv", lambda: (
        generate_audience_segments_df(profile)
        .to_csv(output_dir / "audience_segments.csv", index=False)
    ))
    write("ad_copy_library.csv", lambda: (
        generate_ad_copy_library_df(profile)
        .to_csv(output_dir / "ad_copy_library.csv", index=False)
    ))
    write("budget_allocation.xlsx", lambda: (
        generate_budget_allocation_xlsx(profile)
        .save(output_dir / "budget_allocation.xlsx")
    ))

    if not no_docs:
        write("monthly_report.pdf", lambda:
              generate_monthly_report_pdf(profile, output_dir / "monthly_report.pdf"))
        write("strategy_brief.docx", lambda:
              generate_strategy_brief_docx(profile, output_dir / "strategy_brief.docx"))


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(client_ids: list[str], output_dir: Path, no_docs: bool) -> None:
    expected = ["campaign_performance.csv", "audience_segments.csv",
                "ad_copy_library.csv", "budget_allocation.xlsx"]
    if not no_docs:
        expected += ["monthly_report.pdf", "strategy_brief.docx"]

    table = Table(title="Generated Files", header_style="bold blue")
    table.add_column("Client", style="cyan")
    table.add_column("Files", style="green")
    table.add_column("Path")

    for cid in client_ids:
        d = output_dir / cid
        present = [f for f in expected if (d / f).exists()]
        table.add_row(cid, f"{len(present)}/{len(expected)}", str(d))

    console.print(table)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--clients", default=",".join(ALL_CLIENTS), show_default=True,
              help=f"Comma-separated client IDs. Choices: {', '.join(ALL_CLIENTS)}")
@click.option("--output-dir", default="data/seeds", show_default=True, type=click.Path())
@click.option("--raw-dir", default="data/raw", show_default=True, type=click.Path(),
              help="Path to normalised Kaggle raw data (from download-kaggle).")
@click.option("--seed", default=42, show_default=True, type=int)
@click.option("--no-docs", is_flag=True, default=False,
              help="Skip PDF/DOCX generation — CSV/XLSX only.")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("-v", "--verbose", is_flag=True, default=False)
def cli(clients, output_dir, raw_dir, seed, no_docs, dry_run, verbose):
    """Generate per-client seed data for the Argus GraphRAG demo dataset."""
    import sys
    client_ids = [c.strip() for c in clients.split(",") if c.strip()]
    invalid = [c for c in client_ids if c not in ALL_CLIENTS]
    if invalid:
        console.print(f"[red]Unknown client IDs: {invalid}[/red]")
        sys.exit(1)

    out_path = Path(output_dir)
    raw_path = Path(raw_dir)

    console.print(f"\n[bold blue]Argus Seed Data Generator[/bold blue]")
    console.print(f"  Clients  : {', '.join(client_ids)}")
    console.print(f"  Output   : {out_path}")
    console.print(f"  Raw data : {raw_path}")
    console.print(f"  Seed     : {seed}")
    console.print(f"  Docs     : {'[red]disabled[/red]' if no_docs else '[green]enabled[/green] (Jinja2 templates)'}")

    if dry_run:
        console.print("\n[yellow]Dry run — no files will be written.[/yellow]")
        for cid in client_ids:
            spec = CLIENT_SPECS[cid]
            console.print(f"  Would generate: {cid} ({spec['company_name']}, {spec['industry']})")
        return

    set_seed(seed)

    # Load real data if available
    raw_campaigns = _load_raw_campaigns(raw_path)
    raw_social = _load_raw_social_ads(raw_path)

    if raw_campaigns is None:
        console.print("  [yellow]No raw campaign data found — using Faker-generated synthetic data[/yellow]")
        console.print("  [dim]Tip: run `poetry run download-kaggle` first for real data[/dim]")

    console.print()
    for cid in client_ids:
        console.print(f"[bold]{cid}[/bold] ({CLIENT_SPECS[cid]['company_name']})")
        profile = build_client_profile(cid, raw_campaigns, raw_social)
        generate_client(profile, out_path / cid, no_docs, verbose)

    console.print()
    print_summary(client_ids, out_path, no_docs)
    console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    cli()
