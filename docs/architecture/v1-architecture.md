# V1 architecture

```text
TfL Line API
  -> typed Python ingestion
  -> Postgres raw system of record
  -> DuckDB raw snapshot
  -> dbt staging/intermediate/marts
  -> read-only FastAPI
  -> bundled reliability dashboard
```

Apache Airflow owns the five-minute operational workflow and the daily
reference-data workflow. The status workflow ingests, snapshots, transforms,
validates and checks API readiness in sequence.

Postgres preserves raw payloads and pipeline-run history. DuckDB is a
rebuildable single-writer analytical file. The API mounts that file read-only
and receives no Postgres credentials. This keeps dashboard traffic outside the
ingestion transaction boundary.

The V1 intelligence feature is coverage-aware observed reliability: daily and
rolling uptime, inferred disruption episodes, recovery time and freshness.
Missing polling buckets are represented by coverage rather than classified as
good service.

The production shape is one Docker Compose host behind Nginx Proxy Manager.
FastAPI and the curated Metabase surface are public. Metabase administration is
authenticated; Postgres and Airflow remain private.
