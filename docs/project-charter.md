# TfL Intel — Project Charter

The what and why of the project. The detailed how/when lives in
[portfolio-roadmap.md](portfolio-roadmap.md); operations live in
[runbook.md](runbook.md).

---

## Problem statement

TfL publishes the live status of every tube line, but that information is
**ephemeral** — the moment a disruption clears, it vanishes. There is no
accessible history, so questions that matter to passengers, analysts, and
anyone choosing where to live or how to commute are unanswerable:

- Which line is the least reliable, and by how much?
- When do disruptions cluster — rush hour, weekends, particular seasons?
- How long does a typical disruption take to recover?
- Is a given line getting better or worse over time?

A live API call can only ever describe *now*. **TfL Intel continuously
captures ephemeral operational status and turns it into durable, queryable
reliability intelligence** — the difference between a weather report and a
climate record.

## Objectives

1. **Capture** — run an idempotent, retried, observable EL pipeline against
   the TfL Line API on a schedule, accumulating an append-only history of
   status observations with full run lineage.
2. **Model** — transform raw observations into tested analytics marts:
   current status, uptime %, disruption-minutes, disruption events, and
   mean time to recovery per line.
3. **Serve** — expose the marts through a clean, read-only JSON API that is
   decoupled from ingestion.
4. **Show** — make the insight legible to a non-engineer in 30 seconds via a
   dashboard (status board, reliability leaderboard, uptime trends).
5. **Operate** — run it like production: CI on every push, enforced data
   freshness, monitored scheduled runs, live deployment.
6. **Demonstrate** — cover the full data-engineering + analytics-engineering
   lifecycle credibly enough to anchor a portfolio and CV.

## Success criteria (measurable)

| # | Criterion | Target |
|---|---|---|
| 1 | Unattended scheduled ingestion | ≥ 30 consecutive days, ≥ 99% run success |
| 2 | Reliability metrics served | uptime %, disruption-minutes, MTTR per line via API |
| 3 | CI | green on every push; coverage ≥ 80% enforced |
| 4 | Transform layer | dbt models with passing data tests + published lineage docs |
| 5 | Consumption | dashboard understandable by a non-engineer in 30 seconds |
| 6 | Deployment | public live URL for API + dashboard |
| 7 | Data quality | freshness SLA enforced (alert if stale > 15 min) |

## Scope

**In scope (current horizon):** London Underground (tube mode) line status;
Postgres raw layer; DuckDB/dbt analytics; FastAPI serving; scheduled batch
ingestion (5-minute cadence); one finished intelligence feature.

**Out of scope (deliberately, for now):** other TfL modes (bus, rail —
schema already supports them via `mode_name`); streaming infrastructure
(Redpanda/Kafka) — 5-minute batch is honest for this data's cadence; review
scraping (synthetic data only until sourcing/ToS is resolved); deep-learning
forecasting before a statistical baseline exists.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| TfL API rate limits / outages | Registered app key; retry with backoff; failed runs recorded, never silent |
| Local machine can't run 24/7 | Move scheduling to a deployed worker (Fly.io/Railway) — part of Phase 4 |
| Snapshot refresh races the API | API opens per-query read-only connections; refresh replaces the file atomically |
| Parser breaks on unseen payloads | Raw JSONB retained on every row — history is reprocessable |
| Scope creep (ML/LLM ambitions) | Charter scope + ADR-001; one intelligence feature finished before any new one starts |

---

## Master checklist

### Done — foundation (V1)

- [x] Layered ingestion package: clients / parsers / models / loaders / jobs
- [x] Deterministic IDs + `ON CONFLICT` → idempotent re-runs, proven by integration test
- [x] Run tracking (`raw.pipeline_runs`) with success/failure states and counts
- [x] Raw payload retention (JSONB) for reprocessability
- [x] Retry with exponential backoff on the TfL client (5xx/timeouts only)
- [x] DuckDB analytics snapshot + read-only FastAPI serving layer
- [x] Health vs readiness endpoints; freshness as a queryable metric
- [x] Strict tooling: uv, ruff, mypy (strict), structlog, Docker secrets
- [x] GitHub Actions CI (lint, format, types, unit tests)
- [x] Docs: ADRs, source audit, architecture, roadmap, runbook, charter

### Phase A — visibility & polish (hours)

- [ ] Push branch, open PR, merge to main — CI badge goes green
- [ ] Add `.pre-commit-config.yaml` (ruff + ruff-format + mypy) — the dep is
      already declared, wire it or drop it
- [ ] Enforce coverage: `--cov=tfl_intel --cov-fail-under=80` in CI
- [ ] Point `tests/serving/conftest.py` at the real `sql/duckdb/*.sql`
      instead of retyped inline SQL, so a bug in production SQL fails a test
- [ ] Dockerfile for the API image (replace the compose `--with ...` list,
      which duplicates pyproject and will drift)

### Phase B — run it over time (the value unlock, days)

- [ ] Replace the shell loop with real scheduling (cron first; Dagster when
      there is more than one job to orchestrate)
- [ ] Reliability marts from accumulated history:
  - [ ] uptime % per line (share of observations in Good Service)
  - [ ] disruption-minutes per line per day/week
  - [ ] disruption events via status transitions (good → disrupted → good)
  - [ ] mean time to recovery per line
- [ ] Serve them: `/api/v1/lines/reliability`, `/api/v1/lines/{id}/uptime`
- [ ] End-to-end failure-path test: client raises → run row ends `failed`

### Phase C — analytics engineering (days)

- [ ] dbt (dbt-duckdb): staging → intermediate → marts
- [ ] dbt data tests: `not_null`, `unique`, `accepted_values` on severity,
      relationships between lines and observations
- [ ] dbt docs + lineage graph published (screenshot in README)

### Phase D — the face (days)

- [ ] Dashboard (Metabase or small frontend): colour-coded live status
      board, "least reliable line this week" leaderboard, uptime trend
- [ ] Screenshot at the top of the README

### Phase E — operate like production (days)

- [ ] Deploy API + scheduled ingester to Fly.io/Railway — public URL
- [ ] Freshness SLA: alert/fail when `minutes_since_latest_success` > 15
- [ ] Data-quality gate: flag runs inserting 0 rows unexpectedly
- [ ] Integration tests in CI via Postgres service container

### Phase F — one finished intelligence feature (pick one)

- [ ] Statistical baseline: P(line disrupted at hour H, weekday D) from
      history — deliberately before any deep learning
- [ ] *or* review theme-tagging over the synthetic reviews corpus

### Stretch — range signals

- [ ] Property-based test (hypothesis) on `make_status_fingerprint`
- [ ] Batch inserts (`executemany`/COPY) when observation volume justifies it
- [ ] Second TfL mode (elizabeth-line or overground) to prove the
      mode-parameterized design
