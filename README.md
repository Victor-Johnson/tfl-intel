# TfL Intel

**TfL Passenger Pain Intelligence Platform** is a professional data engineering
and analytics engineering portfolio project for understanding passenger pain
across TfL operational status data and complaint or review themes.

## V1 Scope

V1 proves a clean vertical slice:

```text
TfL Line API -> Python ingestion -> Postgres raw schema
  -> dbt models later -> Metabase dashboard later
```

The first implementation focuses on package structure, source ingestion
scaffolding, parsing, deterministic IDs, tests, source audit notes, and clear
commands for continuing the project.

## Out Of Scope For V1

Redpanda, MinIO, Dagster, Grafana, LSTM forecasting, LLM briefing, production
orchestration, and external review scraping are intentionally delayed. Review
examples in this repo are synthetic and exist only to shape future theme logic.

## Architecture Summary

The V1 ingestion path fetches the TfL Line API with a small `httpx` client,
parses one observation per line status item, and writes raw observations and
metadata to Postgres. Review theme work starts with a small YAML rules file and
synthetic sample rows.

## Local Setup

```bash
uv sync
cp .env.example .env
```

TfL credentials are optional for local tests. The public Line/Status endpoint
can be explored without hardcoding secrets.

## Daily Commands

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run python -m tfl_intel.ingestion.jobs.ingest_line_status
```

## Local API ingestion smoke test

```bash
docker compose up -d postgres

uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

docker exec -it tfl_intel_postgres psql -U tfl_intel -d tfl_intel -c "SELECT COUNT(*) FROM raw.pipeline_runs;"

docker exec -it tfl_intel_postgres psql -U tfl_intel -d tfl_intel -c "SELECT COUNT(*) FROM raw.tfl_line_status_observations;"
```

## Current Status

- [x] Python `src/` package scaffold
- [x] TfL Line/Status client skeleton
- [x] Line status parser and unit tests
- [x] Deterministic ID helpers
- [x] Safe `.env.example`
- [x] Review theme scaffold with synthetic data
- [x] Architecture and ADR docs
- [x] Postgres raw schema
- [ ] dbt models
- [ ] Metabase dashboard
