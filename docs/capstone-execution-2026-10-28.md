# Capstone execution evidence: 2026-10-28

This is a local verification record for the
[four-day plan](four-day-capstone-plan.md), not a production sign-off. The
working tree was already dirty and remains uncommitted. Baseline HEAD:
`9e60a2b`. Tests below exercised the working tree, not that commit alone.

## Verified locally

| Layer | Evidence | Result |
|---|---|---|
| Ingestion | `make check`; focused 429, empty-response, malformed-poll tests; isolated `REQUIRE_INTEGRATION_DB=1` Postgres tests | 67 Python tests passed in the final full check, 5 integration tests skipped there; all 5 passed separately against a temporary Postgres project. A replay of one run ID inserted zero new rows; a second run ID inserted another observation. A write failure after insert rolled back observations but retained a failed run. Retry-After missing/header-date and exhausted timeout paths passed; a 429 marked the job failed after its bounded attempts. |
| Modeling | `make dbt-ci` with synthetic clock-change and timeline fixtures | dbt build passed with 96 passes and one exposure no-op. Spring/autumn local days used 276/300 expected buckets; the scenario fixture checked worst status, latest run per bucket, missing-poll gap, two episodes, 50% observed uptime, and low coverage. The new line-hour mart passed its 50% fixture and grain assertion. |
| Processing | Isolated real TfL ingestion -> candidate DuckDB -> dbt -> invariant validation -> atomic promotion | Four manual status polls and reference ingestion succeeded. A candidate with an invalid daily mart was rejected while the live snapshot stayed readable; a clean rebuild then promoted. Tool container and API used the same locked DuckDB version. |
| Serving | Isolated API on port 8001, 30 local requests to current-status | `/ready` returned ready, current status returned 20 lines, mode summary returned five modes. Current-status p50 was 11.3 ms and p95 was 12.62 ms. During a concurrent refresh, 720 requests over 38.1 seconds returned zero errors and saw only complete old or new snapshot run IDs. This is a tiny local sample, not capacity evidence. |
| Orchestration | `airflow dags test` in the isolated project | Status and reference DAG tests succeeded. Status task order was ingest -> snapshot -> dbt -> validate -> promote -> API ready -> BI publish. A deliberately unreachable TfL URL recorded a failed raw run and left downstream tasks unrun; the task was still `up_for_retry` when the scheduler was stopped, so retry exhaustion was not proven. |
| BI security | Published the initial ten marts to isolated Postgres `analytics`; tested `SET ROLE metabase_reader` | Reader could select 20 current lines from `analytics` and was denied `raw` schema access. `collection_health.sql` ran as that role and later reported the snapshot stale at 19.8 minutes. |
| Traveler BI prototype | Published eleven fixture marts to a separate isolated Postgres database; provisioned private local Metabase on port 3001 | Seven traveler cards executed through Metabase. The dashboard line filter returned Bakerloo; a second provisioning call reused dashboard ID 1. The local data is synthetic fixture data, not live or publicly shared. |
| 90-day retention | Isolated Postgres integration test plus operational dump/restore probe | Expired observations and unreferenced runs were pruned while recent rows survived. A corrected custom-format dump restored 88 raw rows into a disposable database. The production backup/retention job was not run end-to-end. |

The final isolated live snapshot had 88 raw status rows across 20 lines and
five modes. An earlier 66-row snapshot occupied 5,255,168 bytes. A
representative grouped `EXPLAIN ANALYZE` reported about
0.0017 seconds, with a largest line group of six rows and median of three.
These numbers justify retaining the single-host design **for this sample**;
they do not establish a production-scale threshold. Full-versus-incremental
should be revisited after sustained live history is collected.

The [Central-line metric trace](metric-lineage-example.md) joins raw payloads
to successful runs and follows their IDs through the DuckDB snapshot,
canonical five-minute buckets, event model, daily mart, and API. At the
four-poll snapshot it yielded 0/4 observed Good Service, 4/288 full-day
coverage (1.39%, insufficient), and two unresolved observed episodes after a
long sampling gap. This is not evidence that the line was disrupted all day.

`make production-config`, shell syntax checks for the changed scripts,
`ruff format --check .`, and `git diff --check` also passed. The fixture-only
semantic tests are not applied to live TfL rows; live builds use generic
grain and denominator invariants. In the 90-day Metabase query, the repeated
autumn Sunday 01:00 hour had 168 expected samples versus 156 for Sunday
02:00, showing the DST denominator was counted by actual UTC slots.

## Issues found and addressed

- The one-off tool container originally resolved a newer DuckDB than the API.
  Its snapshot was unreadable by the API. Tool scripts now use `uv.lock`.
- dbt uses the database basename as a catalog. A candidate filename with an
  extra dot failed to build; `tfl_intel_building.duckdb` works.
- A freshness *view* built in the candidate retained that candidate catalog
  name after promotion. The mart is materialized; the API and validator now
  calculate age from its timestamp when queried.
- The existing Postgres volume rejected the current password file and had
  zero raw observations. It was not rotated or replaced. All integration and
  live-data checks used a separate Compose project on port 55432.
- The backup script's `pg_dump --file -` produced a zero-byte host file.
  Removing `--file -` made stdout redirection work; a 52,588-byte isolated
  dump restored all 88 raw observations. Both backup archives now receive
  non-empty and `pg_restore --list` checks before the operational dump is
  restored and 90-day pruning can run.

## Still open

- [ ] Replace example production Metabase credentials, test the traveler
      dashboard as a viewer only after a sharing/security decision, and
      decide whether to publish it. The local dashboard uses isolated strong
      credentials and remains private.
- [ ] Configure and test an external alert for failed polling and stale served
      data. The failure injection proved `up_for_retry`, not exhausted retries
      or alert delivery.
- [ ] Add a separate publication timestamp/version if a BI freshness SLA is
      needed; the current field is the newest ingestion run in the snapshot.
- [ ] Reconcile the password file with the existing Postgres volume using a
      deliberate migration or credential rotation. Do not replace the volume
      simply to make a test pass.
- [ ] Collect real 30-day history, report coverage and refresh timings over
      that window, and repeat performance tests at meaningful scale.
- [ ] Complete backup restore, deployment/rollback, HTTPS/external checks,
      and an unfamiliar-user dashboard walkthrough. None was claimed here.

The temporary Airflow scheduler remains stopped. The isolated Postgres and
Metabase services are running for the private fixture demo at
`http://127.0.0.1:3001/dashboard/1`; the read-only API demo is at
`http://127.0.0.1:8001/dashboard`. Both snapshots are finite and will become
stale. Neither is the production deployment.
