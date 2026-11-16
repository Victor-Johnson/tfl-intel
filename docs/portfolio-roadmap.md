# TfL Intel — current state and next steps

## Portfolio state

The V1 vertical slice is complete: scheduled ingestion, durable raw storage,
dbt transformations, data tests, reliability marts, API, dashboard, CI/CD, and
single-host deployment are represented in working code and documentation.

| Capability | Current evidence |
|---|---|
| Ingestion | Retried, idempotent, run-tracked Python jobs |
| Storage | Postgres raw history and rebuildable DuckDB snapshot |
| Transformation | dbt staging, intermediate, dimensions, facts, and marts |
| Quality | Python tests, dbt tests, runtime validation, readiness checks |
| Orchestration | Five-minute status and daily reference Airflow DAGs |
| Consumption | Read-only API and responsive reliability dashboard |
| Operations | CI/CD, production Compose policy, HTTPS contract, backups |

## Recommended next iteration

1. Accumulate enough continuous production history for seven-day rankings to
   reach reliable coverage.
2. Add timetable and planned-work sources so expected observations reflect
   operating hours and planned disruptions can be segmented.
3. Export freshness and failure metrics to an alerting service.
4. Publish generated dbt documentation behind private or static hosting.
5. Add a statistical forecasting baseline only after the historical dataset is
   large enough for time-based validation.

## Deliberately out of scope

Redpanda, object storage, distributed compute, deep-learning forecasting, LLM
briefings, review scraping, and a separate frontend framework are not required
to prove the V1 portfolio story. They should be added only in response to a
measured scaling or product need.
