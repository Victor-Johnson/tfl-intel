# TfL Intel — interview walkthrough

## One-minute opening

TfL publishes current line status, but a resolved status disappears. I built a
small production-shaped data platform that captures that changing state every
five minutes and turns it into an auditable history of observed reliability.
The key product decision is that missing observations are shown as coverage,
never silently counted as good service.

## Walkthrough order

1. **Dashboard:** filter the five transport modes, compare status mix and
   time-of-week patterns, then show coverage, daily trends, and episodes.
2. **Architecture:** explain why Postgres is the durable operational store and
   DuckDB is a rebuildable analytical read model.
3. **Ingestion:** show selective retries, deterministic identifiers, raw-payload
   retention, transaction boundaries, and database-backed run tracking.
4. **dbt:** follow staging through status intervals into disruption facts and
   reliability marts; show generic and singular tests.
5. **Airflow:** show the six-step status DAG, including validated BI
   publication, and the daily reference-data DAG.
6. **Serving:** demonstrate that FastAPI reads DuckDB but has no Postgres
   credentials, then query the OpenAPI page and drill into the curated
   read-only Metabase workspace.
7. **Delivery:** show CI, the production Compose policy, private administration,
   HTTPS proxying, and database backups.

## Questions to invite

- How does replay safety work?
- Why not query Postgres directly from the dashboard?
- How is a disruption episode inferred from snapshots?
- Why is observed uptime separated from coverage?
- What would need to change for horizontal scaling?

## Honest boundaries

- The metric is an observation-based estimate, not an official TfL SLA.
- Planned and unplanned disruptions are not separated in V1.
- Expected coverage uses calendar-day buckets rather than operating timetables.
- DuckDB intentionally assumes a single writer.
- Alert delivery is a future integration; freshness signals already exist.
- Predictive ML is deliberately deferred until enough coverage-labelled
  history exists for defensible training and evaluation.

## Evidence

- Python unit, component, and real-Postgres integration tests.
- dbt contracts, generic tests, singular tests, and generated lineage.
- Runtime mart validation before readiness.
- Five-minute Airflow scheduling with retries and one active run.
- Automated deployment only after every CI gate succeeds.

Data provided by Transport for London. This is an unofficial portfolio project.
