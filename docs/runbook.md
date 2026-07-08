# Runbook: running the pipeline end to end

How to take the platform from a fresh clone to a serving API, plus how to
operate and troubleshoot it day to day.

## Prerequisites

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/)
- No TfL API key is required for the public Line/Status endpoints
  (`TFL_APP_KEY` in `.env` raises rate limits if you have one).

## First-time setup

```bash
uv sync
cp .env.example .env
mkdir -p secrets
cp secrets.example/postgres_password.txt.example secrets/postgres_password.txt

make postgres-up      # start Postgres (docker compose)
make postgres-init    # apply sql/postgres/01..04 (idempotent)
```

## The pipeline, end to end

```text
TfL Line API -> ingestion job -> Postgres raw -> DuckDB snapshot -> FastAPI
```

```bash
# 1. Ingest: fetch current line status, parse, load into Postgres raw.
#    Safe to re-run: deterministic IDs + ON CONFLICT make re-runs no-ops.
make ingest-line-status

# 2. Transform: snapshot Postgres raw into DuckDB and rebuild the
#    analytics marts (current status, summary, freshness).
make duckdb-refresh

# 3. Serve: read-only JSON API over the DuckDB marts on :8000.
make api-docker

# 4. Verify.
make smoke-api                      # or open http://localhost:8000/docs
```

The API reads a DuckDB *file snapshot*, so new ingestion runs are not visible
to the API until the next `make duckdb-refresh`.

## Continuous ingestion (interim scheduler)

Until proper orchestration lands, a shell loop accumulates observations:

```bash
while true; do
  uv run python -m tfl_intel.ingestion.jobs.ingest_line_status \
    || echo "run failed $(date)"
  sleep 300
done
```

Every run writes a row to `raw.pipeline_runs` (started/success/failed plus
record counts), so gaps and failures are visible in the data:

```bash
docker exec -it tfl_intel_postgres psql -U tfl_intel -d tfl_intel \
  -c "SELECT ingestion_run_id, status, records_inserted, started_at
      FROM raw.pipeline_runs ORDER BY started_at DESC LIMIT 10;"
```

Freshness is also served by the API: `GET /api/v1/pipeline/freshness`
reports `minutes_since_latest_success`.

## Tests and checks

```bash
make check                     # ruff + mypy + unit tests (what CI runs)
uv run pytest -m integration   # loader tests against local Postgres
```

Integration tests roll back their transaction, so they leave no rows behind.

## Troubleshooting

**`ModuleNotFoundError: tfl_intel` or `Permission denied` from `uv run`.**
The host `.venv` was corrupted by a container-side `uv` command (the compose
services mount the repo at `/workspace` and run as root). Fix:
`rm -rf .venv && uv sync`. Prevention: the compose services set
`UV_PROJECT_ENVIRONMENT` so container uv never touches the host venv — keep
that on any new service that mounts the repo.

**API returns 500 on timestamp-bearing endpoints.**
Check that `pytz` is installed. It is never imported directly, but duckdb
lazily imports it to convert TIMESTAMPTZ results; do not remove it from
`pyproject.toml` (there is a comment there explaining this).

**`/ready` returns `not_ready`.**
The DuckDB file is missing or the analytics tables have not been built yet —
run `make duckdb-refresh` and check the `missing_tables` field in the
response.
