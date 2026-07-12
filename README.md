# Salary Fairness API

Compare a salary against **BLS OEWS** wage estimates, with an optional **H-1B LCA** overlay. Milestone 1 is data ingest + compare API only (no UI).

## Stack

- Python 3.12+, FastAPI, SQLAlchemy 2, Alembic
- Postgres 16 (Docker Compose)
- `uv` for dependency management

## Quick start (fixtures)

```bash
# 1. Start Postgres (requires Docker Desktop running + WSL integration)
docker compose up -d
# On some WSL setups: docker.exe compose up -d

# 2. Install deps
uv sync

# 3. Migrate
cp .env.example .env   # optional
uv run alembic upgrade head

# 4. Ingest sample data
uv run python -m ingest.oews data/fixtures/oews_sample.csv
uv run python -m ingest.lca data/fixtures/lca_sample.csv

# 5. Run API
uv run uvicorn app.main:app --reload --port 8000
```

Health: `GET http://localhost:8000/health`  
Meta: `GET http://localhost:8000/v1/meta`  
Compare:

```bash
curl -s http://localhost:8000/v1/compare \
  -H 'Content-Type: application/json' \
  -d '{
    "soc_code": "15-1252",
    "job_title": "Software Developer",
    "area_code": "42660",
    "state": "WA",
    "current_salary": 145000
  }'
```

## Full datasets

1. **OEWS** — download metro/state/national tables from [BLS OEWS tables](https://www.bls.gov/oes/tables.htm). Place files under `data/raw/` (gitignored).
2. **LCA** — download one OFLC LCA disclosure file from [DOL OFLC Performance Data](https://www.dol.gov/agencies/eta/foreign-labor/performance). Place under `data/raw/`.

Then:

```bash
uv run python -m ingest.oews data/raw/your_oews_file.xlsx --year 2024
uv run python -m ingest.lca data/raw/your_lca_file.xlsx
```

Column aliases for common BLS/DOL headers are supported (see `ingest/oews.py` and `ingest/lca.py`).

## Compare behavior

- **Authoritative verdict** uses OEWS p25–p75 for the given `soc_code`, preferring metro `area_code`, then state, then national.
- **LCA** is informational when at least `LCA_MIN_SAMPLE` (default 30) certified filings match.
- Free-text job title → SOC mapping is **not** in M1; pass `soc_code` explicitly.

## Clean LCA data

After loading disclosure files:

```bash
uv run python -m ingest.clean_lca --dry-run
uv run python -m ingest.clean_lca
```

This drops fixture rows, Certified-Withdrawn, and wages outside `LCA_WAGE_MIN`/`LCA_WAGE_MAX` (default $20k–$500k), and backfills `fiscal_year` from DOL case numbers (`I-200-25-...` → 2025). Compare matching prefers SOC and uses Certified-only rows.

## Milestone 2 (not implemented)

Fuzzy title→SOC mapping, multi-quarter LCA merge, YoE/level adjustments, Azure deploy, UI.
