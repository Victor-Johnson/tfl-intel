# TfL Intel

![CI](https://github.com/Victor-Johnson/tfl-intel/actions/workflows/ci.yml/badge.svg)

**TfL Transport Intelligence Platform** is a professional data engineering and
analytics engineering portfolio project for understanding passenger experience
across TfL operational status data and future complaint or review themes.

## V1 Scope

V1 proves a clean vertical slice:

```text
TfL Line API -> Python ingestion -> Postgres raw schema
  -> DuckDB analytics snapshot -> FastAPI serving layer
```

The first implementation focuses on package structure, source ingestion
scaffolding, parsing, deterministic IDs, tests, source audit notes, and clear
commands for continuing the project.

## Out Of Scope For V1

Redpanda, MinIO, Dagster, Grafana, LSTM forecasting, LLM briefing, production
orchestration, and external review scraping are intentionally delayed. Review
examples in this repo are synthetic and exist only to shape future theme logic.

## Architecture

```text
TfL API -> Postgres raw layer -> DuckDB analytics layer -> FastAPI serving layer
```

The V1 ingestion path fetches the TfL Line API with a small `httpx` client,
parses one observation per line status item, and writes raw observations and
metadata to Postgres.

Postgres is the raw source of truth because it stores ingestion runs, raw JSON
payloads, and append-style observations with durable operational semantics.
DuckDB is used as an analytical read model because it can snapshot the raw
tables into local columnar analytics tables that are simple to query and easy to
ship with a portfolio demo. FastAPI reads from DuckDB so dashboard consumers get
clean read-only JSON without coupling the API to TfL ingestion or exposing raw
Postgres tables directly.

Docker secrets provide the Postgres password to containers through
`/run/secrets/postgres_password`. The secret file lives under ignored
`secrets/`; the committed `secrets.example/` directory shows the expected local
shape without committing credentials.

## Local Setup

```bash
uv sync
cp .env.example .env
mkdir -p secrets
cp secrets.example/postgres_password.txt.example secrets/postgres_password.txt
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

## Local Serving Smoke Test

```bash
docker compose up -d postgres

uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

docker compose run --rm --entrypoint /workspace/scripts/refresh_duckdb_from_postgres.sh duckdb

docker compose up -d api

curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/v1/lines/current-status
curl http://localhost:8000/api/v1/lines/status-summary
curl http://localhost:8000/api/v1/pipeline/freshness
```

## API Endpoints

```text
GET /health
GET /ready
GET /api/v1/lines/current-status
GET /api/v1/lines/status-summary
GET /api/v1/lines/{line_id}/history?limit=50
GET /api/v1/pipeline/latest-run
GET /api/v1/pipeline/freshness
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
- [x] DuckDB analytics snapshot
- [x] FastAPI read-only serving layer
- [ ] dbt models
- [ ] Metabase dashboard
