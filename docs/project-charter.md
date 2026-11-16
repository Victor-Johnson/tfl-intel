# TfL Intel — project charter

## Problem

TfL publishes current rail and tram line status, but a status disappears when
conditions change. TfL Intel captures that ephemeral state across five modes
and turns it into a durable, queryable record of observed reliability.

## Objectives

1. Capture status every five minutes through retried, idempotent ingestion.
2. Preserve raw evidence and operational run metadata in Postgres.
3. Build tested DuckDB/dbt marts for uptime, coverage and disruption episodes.
4. Serve the results through a read-only API and accessible dashboard.
5. Operate the platform through Airflow, CI/CD, readiness checks and backups.
6. Present the engineering decisions honestly as a portfolio case study.

## Success criteria

| Criterion | V1 target | State |
|---|---|---|
| Scheduled ingestion | Five-minute Airflow DAG with retry | Implemented |
| Reliability models | Daily/rolling uptime, events and recovery | Implemented |
| Confidence | Coverage shown separately from uptime | Implemented |
| Transformation | dbt graph with passing tests | Implemented |
| Serving | Typed API, product dashboard, and read-only Metabase BI | Implemented |
| Delivery | Gated CI/CD and production Compose contract | Implemented |
| Operations | Freshness check and recoverable backups | Implemented |
| History | Thirty continuous production days | Pending live accumulation |

## Scope

V1 covers Tube, Elizabeth line, DLR, London Overground, and Tram status,
reference dimensions, raw history, coverage-aware reliability, network
comparisons, a single-host deployment, and portfolio publishing material.

It deliberately excludes streaming infrastructure, distributed compute,
deep-learning forecasts, LLM briefings and external review scraping. Those
features do not improve the evidence required for the first portfolio release.

## Risks and controls

| Risk | Control |
|---|---|
| Source timeout or 5xx | Bounded retry; failed run remains queryable |
| Duplicate replay | Deterministic IDs and conflict-safe inserts |
| Incomplete collection | Separate coverage percentage and quality label |
| Transformation defect | dbt tests plus runtime mart validation |
| Serving affects ingestion | Read-only DuckDB mount; no Postgres API credentials |
| Public administration | Loopback binding; only API joins proxy network |
| Host loss | Daily Postgres dumps with off-host-copy requirement |
| Bad deployment | CI gate, readiness smoke test and previous-revision rollback |

## Portfolio completion checklist

- [x] Layered ingestion and retained raw payloads
- [x] Deterministic IDs and real-Postgres replay test
- [x] Airflow scheduling and pipeline-run observability
- [x] dbt staging, intermediate, dimensions, facts and marts
- [x] Generic, singular and runtime data-quality gates
- [x] FastAPI endpoints and coverage-aware dashboard
- [x] Schema-restricted Metabase publication and curated BI question pack
- [x] CI/CD, production Compose policy and backup automation
- [x] Recruiter-first README, case study, article and visual assets
- [ ] Point DNS and Nginx Proxy Manager at the deployed API
- [ ] Publish the prepared project and article in the portfolio CMS
