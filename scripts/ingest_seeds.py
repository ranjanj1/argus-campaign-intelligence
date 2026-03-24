"""
Seed data ingestion script.

Walks data/seeds/{client_id}/{file} and ingests every file into the
correct pgvector collection + Neo4j graph.

Usage:
    ARGUS_PROFILES=develop python scripts/ingest_seeds.py
    ARGUS_PROFILES=develop python scripts/ingest_seeds.py --dry-run
    ARGUS_PROFILES=develop python scripts/ingest_seeds.py --client acme_corp
"""
from __future__ import annotations

import asyncio
import csv
import logging
import sys
from pathlib import Path

import click

# ── Collection mapping ────────────────────────────────────────────────────────
# filename stem → pgvector collection name
FILE_COLLECTION_MAP = {
    "campaign_performance": "campaign_performance",
    "ad_copy_library":      "ad_copy_library",
    "audience_segments":    "audience_segments",
    "strategy_brief":       "client_strategy_briefs",
    "monthly_report":       "monthly_reports",
    "budget_allocation":    "budget_allocations",
}

SEEDS_DIR = Path(__file__).parent.parent / "data" / "seeds"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("ingest_seeds")


# ── Client metadata (for Client node properties not in CSVs) ──────────────────

CLIENT_META: dict[str, dict[str, str]] = {
    "acme_corp":  {"name": "Acme Corp",  "industry": "retail",         "tier": "enterprise"},
    "techflow":   {"name": "TechFlow",   "industry": "technology",     "tier": "standard"},
    "greenleaf":  {"name": "Greenleaf",  "industry": "sustainability",  "tier": "standard"},
    "northstar":  {"name": "Northstar",  "industry": "finance",        "tier": "enterprise"},
}


def _period_from_date(date_str: str) -> str:
    """Convert '2025-02-08' → 'Feb-2025'."""
    from datetime import date
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%b-%Y")
    except ValueError:
        return date_str


async def seed_graph_nodes(
    client_dir: Path,
    client_id: str,
    graph_store: "GraphStoreComponent",  # type: ignore[name-defined]
) -> None:
    """
    Populate structured Neo4j nodes (Client, Campaign, AudienceSegment, Metric)
    from the CSV seed files for one client.
    """
    meta = CLIENT_META.get(
        client_id,
        {"name": client_id.replace("_", " ").title(), "industry": "marketing", "tier": "standard"},
    )

    # ── 1. Upsert Client ──────────────────────────────────────────────────────
    await graph_store.upsert_client(
        id=client_id,
        name=meta["name"],
        industry=meta["industry"],
        tier=meta["tier"],
    )
    logger.info("    graph  Client(%s) upserted", client_id)

    # ── 2. Parse campaign_performance.csv ─────────────────────────────────────
    perf_file = client_dir / "campaign_performance.csv"
    if not perf_file.exists():
        logger.warning("    skip graph seeding — %s not found", perf_file.name)
        return

    # segment_id → list[campaign_id]  (needed when seeding segments)
    seg_campaign_map: dict[str, list[str]] = {}

    with perf_file.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            campaign_id   = row["campaign_id"]
            seg_id        = row.get("audience_segment_id", "")
            period        = _period_from_date(row.get("start_date", ""))

            # Upsert Campaign
            await graph_store.upsert_campaign({
                "id":         campaign_id,
                "name":       row["campaign_name"],
                "channel":    row["channel"],
                "status":     row["status"],
                "start_date": row["start_date"],
                "end_date":   row["end_date"],
                "client_id":  client_id,
            })

            # Upsert key metrics
            for metric_type, col, unit in [
                ("ROAS", "roas",            "x"),
                ("CTR",  "ctr",             "%"),
                ("CPA",  "cpa",             "USD"),
            ]:
                raw = row.get(col, "")
                if raw:
                    await graph_store.upsert_metric(
                        campaign_id=campaign_id,
                        metric_type=metric_type,
                        value=float(raw),
                        period=period,
                        unit=unit,
                    )

            # Track which campaigns target each segment
            if seg_id:
                seg_campaign_map.setdefault(seg_id, []).append(campaign_id)

    logger.info(
        "    graph  %d campaigns seeded from %s",
        sum(len(v) for v in seg_campaign_map.values()) or "?",
        perf_file.name,
    )

    # ── 3. Parse audience_segments.csv ────────────────────────────────────────
    seg_file = client_dir / "audience_segments.csv"
    if not seg_file.exists():
        logger.warning("    skip segment seeding — %s not found", seg_file.name)
        return

    seg_count = 0
    with seg_file.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            seg_id = row["segment_id"]

            # Each segment must be linked to at least one campaign.
            # Use the mapping built from campaign_performance.csv; fall back to
            # a placeholder so the node is still created.
            campaign_ids = seg_campaign_map.get(seg_id, [])
            if not campaign_ids:
                logger.debug("    segment %s has no matching campaign — skipping TARGETS link", seg_id)
                continue

            for campaign_id in campaign_ids:
                await graph_store.upsert_segment({
                    "id":          seg_id,
                    "name":        row["segment_name"],
                    "age_range":   row.get("age_range", ""),
                    "gender":      row.get("gender", "all"),
                    "platform":    row.get("platform", ""),
                    "client_id":   client_id,
                    "campaign_id": campaign_id,
                })
            seg_count += 1

    logger.info("    graph  %d audience segments seeded from %s", seg_count, seg_file.name)


# ── Core logic ────────────────────────────────────────────────────────────────

async def run(only_client: str | None, dry_run: bool) -> None:
    # Bootstrap DI (imports are deferred so env vars are set first)
    from argus.components.graph_store.graph_store_component import GraphStoreComponent
    from argus.components.ingest.ingest_component import IngestComponent
    from argus.components.vector_store.vector_store_component import VectorStoreComponent
    from argus.di import get_injector

    injector = get_injector()
    vector_store = injector.get(VectorStoreComponent)
    graph_store  = injector.get(GraphStoreComponent)
    ingest       = injector.get(IngestComponent)

    # Initialise schema (idempotent)
    logger.info("Initialising pgvector collections…")
    await vector_store.initialize()
    logger.info("Initialising Neo4j schema…")
    await graph_store.init_schema()

    # Collect files
    client_dirs = sorted(
        d for d in SEEDS_DIR.iterdir()
        if d.is_dir() and (only_client is None or d.name == only_client)
    )
    if not client_dirs:
        logger.error("No client directories found under %s", SEEDS_DIR)
        sys.exit(1)

    total = ok = errors = 0

    for client_dir in client_dirs:
        client_id = client_dir.name
        logger.info("── Client: %s ──────────────────────────", client_id)

        for filepath in sorted(client_dir.iterdir()):
            stem = filepath.stem          # e.g. "campaign_performance"
            collection = FILE_COLLECTION_MAP.get(stem)

            if collection is None:
                logger.warning("  skip  %s — no collection mapping", filepath.name)
                continue

            total += 1
            if dry_run:
                logger.info("  [dry]  %s → %s", filepath.name, collection)
                continue

            logger.info("  ingest %s → %s", filepath.name, collection)
            result = await ingest.ingest_file(
                path=filepath,
                collection=collection,
                client_id=client_id,
            )

            if result.error:
                errors += 1
                logger.error(
                    "  ERROR  %s: %s", filepath.name, result.error
                )
            else:
                ok += 1
                logger.info(
                    "  OK     %s — chunks=%d entities=%d doc_id=%s",
                    filepath.name, result.chunk_count,
                    result.entity_count, result.doc_id,
                )

    if dry_run:
        logger.info("Dry run complete — %d files would be ingested", total)
        return

    logger.info("")
    logger.info("════ Ingest complete ════")
    logger.info("  Total : %d", total)
    logger.info("  OK    : %d", ok)
    logger.info("  Errors: %d", errors)

    # ── Phase 2: seed structured graph nodes (Campaign / Segment / Metric) ────
    logger.info("")
    logger.info("════ Seeding structured graph nodes ════")
    for client_dir in client_dirs:
        client_id = client_dir.name
        logger.info("── Client: %s ──────────────────────────", client_id)
        try:
            await seed_graph_nodes(client_dir, client_id, graph_store)
        except Exception as exc:
            logger.error("  ERROR seeding graph for %s: %s", client_id, exc)
            errors += 1

    logger.info("Graph seeding complete")

    if errors:
        sys.exit(1)


# ── CLI entry point ───────────────────────────────────────────────────────────

@click.command()
@click.option("--client", default=None, help="Ingest only this client (e.g. acme_corp)")
@click.option("--dry-run", is_flag=True, help="Print files without ingesting")
def cli(client: str | None, dry_run: bool) -> None:
    """Ingest seed data from data/seeds/ into pgvector + Neo4j."""
    asyncio.run(run(only_client=client, dry_run=dry_run))


if __name__ == "__main__":
    cli()
