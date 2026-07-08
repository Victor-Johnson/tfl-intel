# TfL Transport Intelligence Architecture

```text
TfL API -> Postgres raw layer -> DuckDB analytics layer -> FastAPI serving layer
```

## Layers

Postgres is the system of record for raw ingestion. It stores pipeline run
metadata, raw TfL payloads, and one line-status observation per line-status item
per ingestion run.

DuckDB is the analytical read model. The refresh script snapshots raw Postgres
tables into `raw_snapshot` and builds dashboard-friendly tables in `analytics`.
This keeps analytical queries separate from ingestion writes and makes the API
fast, deterministic, and easy to demonstrate locally.

FastAPI is the read-only serving layer. It reads from DuckDB and exposes stable
JSON endpoints for consumers such as dashboards, notebooks, or portfolio demos.
It does not call the TfL API and does not perform ingestion.

## Operating Flow

```bash
docker compose up -d postgres
uv run python -m tfl_intel.ingestion.jobs.ingest_line_status
docker compose run --rm --entrypoint /workspace/scripts/refresh_duckdb_from_postgres.sh duckdb
docker compose up -d api
```

The DuckDB refresh must run after ingestion for the API to serve fresh data.

## Secrets

Docker Compose provides the Postgres password through
`/run/secrets/postgres_password`. The real file is stored in ignored
`secrets/postgres_password.txt`; `secrets.example/postgres_password.txt.example`
documents the required shape.
