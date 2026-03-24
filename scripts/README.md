# Argus Seed Data Scripts

Generates a realistic fake "agency world" dataset for 4 fictional clients across 6 file types. Used to populate the Argus GraphRAG ingest pipeline with coherent, cross-referenced test data.

**No Claude API key required.** PDFs and DOCX files are generated via Jinja2 templates with real metric substitution.

---

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Download real Kaggle data (optional but recommended)
poetry run download-kaggle --verbose

#    OR — no Kaggle account needed:
poetry run download-kaggle --sling-only

# 3. Generate all client files
poetry run seed --verbose

# 4. Verify output
ls data/seeds/acme_corp/
# campaign_performance.csv  audience_segments.csv  ad_copy_library.csv
# budget_allocation.xlsx    monthly_report.pdf      strategy_brief.docx
```

---

## Scripts

### `download_kaggle.py`

Downloads and normalises real marketing datasets into `data/raw/`.

```bash
poetry run download-kaggle [OPTIONS]

Options:
  --output-dir PATH   Where to save raw files  [default: data/raw]
  --sling-only        Download only the free Sling Academy CSV (no Kaggle key)
  -v, --verbose
```

**Datasets downloaded:**

| Dataset | Source | Maps to |
|---------|--------|---------|
| Digital Marketing Campaign (8K rows) | Kaggle: `manishabhatt22/marketing-campaign-performance-dataset` | `campaign_performance` |
| Social Media Advertising | Kaggle: `jsonk11/social-media-advertising-dataset` | `audience_segments` |
| Marketing Campaigns CSV | Sling Academy (free, no login) | Fallback for campaign data |

**Kaggle setup (one-time):**

1. Go to [kaggle.com/settings](https://www.kaggle.com/settings/account) → "Create New Token" → downloads `kaggle.json`
2. Either place `kaggle.json` at `~/.kaggle/kaggle.json`, or copy the values into `.env`:

```bash
cp ../.env.example ../.env
# Edit .env: set KAGGLE_USERNAME and KAGGLE_KEY
```

---

### `seed_data.py`

Reads normalised data from `data/raw/` (or generates synthetic data if unavailable), slices rows per client, and produces 6 files per client in `data/seeds/{client_id}/`.

```bash
poetry run seed [OPTIONS]

Options:
  --clients TEXT      Comma-separated client IDs  [default: all 4]
  --output-dir PATH   Root output directory  [default: data/seeds]
  --raw-dir PATH      Path to normalised Kaggle data  [default: data/raw]
  --seed INTEGER      Faker random seed for reproducibility  [default: 42]
  --no-docs           Skip PDF/DOCX — CSV/XLSX only (faster)
  --dry-run           Print what would be generated, no files written
  -v, --verbose
```

**Examples:**

```bash
# All 4 clients, full output
poetry run seed --verbose

# CSV/XLSX only — no PDF/DOCX
poetry run seed --no-docs --verbose

# Single client
poetry run seed --clients acme_corp --verbose

# Reproducible run
poetry run seed --seed 12345

# Dry run — see what would be generated
poetry run seed --dry-run
```

---

## Output

One directory per client under `data/seeds/`:

```
data/seeds/
├── acme_corp/              # retail, ~$120K/month
│   ├── campaign_performance.csv    # 50 campaigns: spend, ROAS, CTR, conversions
│   ├── audience_segments.csv       # 10 segments: demographics, platform, CTR
│   ├── ad_copy_library.csv         # 20 ad variants: headline, body, CTA, A/B label
│   ├── budget_allocation.xlsx      # 3 sheets: monthly breakdown, per-campaign, forecast vs actual
│   ├── monthly_report.pdf          # 8-10 page performance narrative (ReportLab)
│   └── strategy_brief.docx         # 5-6 page strategy document (python-docx)
├── techflow/               # SaaS, ~$45K/month
├── greenleaf/              # ecommerce, ~$80K/month
└── northstar/              # finance, ~$200K/month
```

**Internal consistency guarantee:** `campaign_performance.csv` spend figures match `budget_allocation.xlsx` Sheet 2 exactly (computed once, never re-randomised). `audience_segment_id` in campaign data is a valid FK to `audience_segments.csv`.

---

## Clients

| Client ID | Company | Industry | Monthly Budget |
|-----------|---------|----------|----------------|
| `acme_corp` | Acme Corporation | Retail | $120K |
| `techflow` | TechFlow Inc. | SaaS | $45K |
| `greenleaf` | GreenLeaf Commerce | eCommerce | $80K |
| `northstar` | NorthStar Financial | Finance | $200K |

---

## Generators

| Module | Output | Data source |
|--------|--------|-------------|
| `generators/campaign_performance.py` | CSV | Sliced from Kaggle data (or Faker fallback) |
| `generators/audience_segments.py` | CSV | Sliced from Kaggle social ads (or Faker fallback) |
| `generators/ad_copy_library.py` | CSV | Faker-generated (no real ad copy dataset available) |
| `generators/budget_allocation.py` | XLSX | Derived from campaign spend figures |
| `generators/monthly_report.py` | PDF | ReportLab + Jinja2 templates (`templates/monthly_report.j2`) |
| `generators/strategy_brief.py` | DOCX | python-docx + Jinja2 templates (`templates/strategy_brief.j2`) |

---

## Argus Ingest Mapping

These files are designed to be ingested by the Argus pipeline with zero transformation:

```bash
# Example ingest commands (once Argus server is running)
curl -X POST http://localhost:8001/v1/ingest/file \
  -F 'file=@data/seeds/acme_corp/campaign_performance.csv' \
  -F 'collection=campaign_performance' \
  -F 'client_id=acme_corp'

curl -X POST http://localhost:8001/v1/ingest/file \
  -F 'file=@data/seeds/acme_corp/monthly_report.pdf' \
  -F 'collection=monthly_reports' \
  -F 'client_id=acme_corp'
```

| Seed file | Argus collection | Parser |
|-----------|-----------------|--------|
| `campaign_performance.csv` | `campaign_performance` | `TableChunker` |
| `audience_segments.csv` | `audience_segments` | `TableChunker` |
| `ad_copy_library.csv` | `ad_copy_library` | `TableChunker` |
| `budget_allocation.xlsx` | `budget_allocations` | `TableChunker` per sheet |
| `monthly_report.pdf` | `monthly_reports` | `PDFReader` |
| `strategy_brief.docx` | `client_strategy_briefs` | `DocxReader` |

---

## Verify Consistency

```python
import pandas as pd

perf = pd.read_csv("data/seeds/acme_corp/campaign_performance.csv")
budget = pd.read_excel("data/seeds/acme_corp/budget_allocation.xlsx", sheet_name="campaign_budget")

assert abs(perf["spend"].sum() - budget["actual_spend"].sum()) < 1.0
print("Consistency check passed")
```
