# Runbook: running the pipeline end to end

How to take the platform from a fresh clone to a serving API, plus how to
operate and troubleshoot it day to day.

## Prerequisites

- Docker + Docker Compose and Buildx
- [uv](https://docs.astral.sh/uv/)
- No TfL API key is required for the public Line/Status endpoints
  (`TFL_APP_KEY` in `.env` raises rate limits if you have one).

## First-time setup

```bash
uv sync --all-groups
cp .env.example .env
mkdir -p secrets
for name in \
  postgres_password airflow_db_password \
  metabase_app_db_password metabase_reader_password; do
  openssl rand -hex 32 > "secrets/$name.txt"
done

# Edit .env: set AIRFLOW_UID to the numeric output of `id -u`, and replace
# AIRFLOW_ADMIN_PASSWORD before starting the Airflow webserver.
chmod 600 .env secrets/*.txt

make postgres-up      # start Postgres (docker compose)
make postgres-init    # apply sql/postgres/01..04 (idempotent)
```

These commands are for a new volume. Do not change only the password file for
an existing Postgres volume: its database role keeps the old password. Back up
and verify a restore before a deliberate role/password rotation.

## The pipeline, end to end

```text
TfL Line API -> ingestion job -> Postgres raw -> DuckDB snapshot -> FastAPI
                                                   \-> Postgres BI -> Metabase
```

```bash
# 1. Ingest: fetch current line status, parse, load into Postgres raw.
#    Replaying the same run ID is deduplicated; a new invocation creates a new
#    run ID and records another observation, even if the status is unchanged.
make ingest-reference-data
make ingest-line-status

# 2. Transform: build a separate DuckDB file, run dbt/tests and invariants,
#    then atomically promote it; a failed build leaves the previous file live.
make duckdb-refresh
make validate-marts

# 3. Serve: read-only JSON API over the DuckDB marts on :8000.
make api-docker

# 4. Explore: publish validated marts and start Metabase on :3000.
make publish-bi
make metabase-up

# 5. Verify.
make smoke-api                      # API docs: http://localhost:8000/docs
# Dashboard: http://localhost:8000/dashboard
# Metabase: http://localhost:3000
```

The API reads a DuckDB *file snapshot*, so new ingestion runs are not visible
to the API until the next successful `make duckdb-refresh`. The tool container
uses `uv.lock`; an ad hoc newer DuckDB can write a file the API cannot open.
Reliability responses include
coverage labels; treat `insufficient` values as directional rather than as
final service-level measurements.

## Airflow schedules

The Compose overlay runs two DAGs:

- `tfl_line_status_pipeline` every five minutes: ingest, snapshot Postgres,
  run `dbt build`, validate publication invariants, check API readiness, then
  publish the BI schema when enabled.
- `tfl_reference_data_pipeline` daily at 03:00 UTC: refresh line and severity
  reference data in Postgres.

```bash
make airflow-up
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  exec airflow-scheduler airflow dags list
```

## Manual continuous-ingestion fallback

If Airflow is deliberately stopped, a shell loop can temporarily accumulate
observations:

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
docker compose exec postgres psql -U tfl_intel -d tfl_intel \
  -c "SELECT ingestion_run_id, status, records_inserted, started_at
      FROM raw.pipeline_runs ORDER BY started_at DESC LIMIT 10;"
```

Freshness is also served by the API: `GET /api/v1/pipeline/freshness`
reports `minutes_since_latest_success`.

## Tests and checks

```bash
make check                     # ruff + mypy + Python tests + dbt build/tests
make dbt-ci                    # deterministic dbt build against a CI fixture
make dbt-docs                  # generate lineage and catalog artifacts
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

For the VPS, HTTPS proxy, deployment workflow, backups, and rollback process,
see [the production deployment guide](../DEPLOYMENT.md).
