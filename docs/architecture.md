# TfL Transport Intelligence Architecture

```text
TfL API -> Postgres raw -> DuckDB snapshot -> dbt marts -> FastAPI/dashboard
                                                   \-> Postgres BI -> Metabase
```

## Layers

Postgres is the system of record for raw ingestion. It stores pipeline run
metadata, raw TfL payloads, and one line-status observation per line-status item
per ingestion run.

DuckDB is the analytical read model. The refresh script snapshots raw Postgres
tables into a separate candidate file's `raw_snapshot`; dbt standardizes
polling history in `staging` and `intermediate`, then builds dashboard-friendly
tables in `analytics`. This keeps analytical queries separate from ingestion
writes and makes the API fast, deterministic, and easy to demonstrate locally.
Validation runs against the
candidate, which is atomically renamed over the live DuckDB file only after
all checks pass. The tool container uses the same locked DuckDB version as the
API; an existing API reader may finish on the prior complete snapshot.

TfL line and status-severity endpoints supply reference metadata. A daily
Airflow DAG stores those records in Postgres, and `analytics.dim_line` plus
`analytics.dim_status_severity` merge them with observed status history. The
observed fallback keeps the analytical layer usable if a reference refresh is
temporarily unavailable.

## Reliability Marts

The transformation layer selects one canonical status per line per five-minute
bucket before calculating reliability. It chooses the worst status when TfL
returns multiple statuses for one line in a response, then chooses the latest
run when manual and scheduled ingestion overlap in a bucket.

`intermediate.line_status_intervals` flags collection gaps longer than ten
minutes. `analytics.disruption_events` models continuous disruption episodes,
while `analytics.line_reliability_daily` and
`analytics.line_reliability_rolling_7d` expose observation-based uptime,
estimated disruption minutes, event counts, and data coverage. Low-coverage
results should not be treated as conclusive reliability measurements. The
daily and rolling marts therefore publish `insufficient`, `provisional`, or
`reliable` coverage labels alongside every uptime estimate.

`analytics.network_status_mix_daily` retains passenger-visible status counts
by mode, while `analytics.network_disruption_hourly` provides a local-time
weekday/hour grain. The API aggregates these daily marts over selectable
windows for mode comparisons, status distribution, and the disruption heatmap.

Every five-minute status DAG run snapshots Postgres into a candidate, executes
`dbt build`, validates invariants, promotes the file, checks API readiness,
and then publishes BI marts. Missing tables,
duplicate poll buckets, invalid percentages, negative durations, freshness
mismatches, and stale data fail the Airflow task instead of silently publishing
an invalid analytical snapshot.

Daily and seven-day collection coverage use Europe/London calendar buckets,
including 23- and 25-hour daylight-saving days. The API calculates ingestion
age from the timestamp in the published snapshot at read time, so stale data
does not appear permanently fresh if polling stops. This is not yet a separate
BI publication timestamp.

FastAPI is the read-only serving layer. It reads from DuckDB and exposes stable
JSON endpoints for consumers such as dashboards, notebooks, or portfolio demos.
It does not call the TfL API and does not perform ingestion. A bundled static
dashboard consumes those same versioned API endpoints, so presentation remains
separate from transformation logic.

Metabase is the self-service BI layer. It does not connect to the actively
refreshed DuckDB file or to raw Postgres tables. After dbt and runtime checks
pass, the Airflow DAG transactionally replaces ten allowlisted tables in the
Postgres `analytics` schema. The `metabase_reader` role has schema usage and
table select privileges only. Metabase stores its own users, questions, and
dashboard definitions in a separate Postgres application database.

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
