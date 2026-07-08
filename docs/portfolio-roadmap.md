# TfL Intel — Portfolio Roadmap & Assessment

A guide for turning this repo from a strong *foundation* into a *proper* data
engineering + analytics engineering portfolio project — with honest commentary
on the work so far and a phased plan to get there.

---

## 1. Where you are right now

### The one-line verdict

You have built a **clean, professional vertical slice** of a data platform. The
*engineering foundations are better than most mid-level data-engineering
portfolios*. What is missing is the part that makes a reviewer stop scrolling:
the pipeline does not yet run over time, and it does not yet *show* anything.

**Current overall: ~7.5 / 10 as a portfolio piece — a strong 8.5+ waiting to happen.**

| Dimension | Score | Notes |
|---|---|---|
| Architecture & structure | 9 / 10 | Clean layering, real separation of concerns |
| Code quality & typing | 8.5 / 10 | Strict mypy, ruff, pydantic-settings, structlog |
| Tooling & professionalism | 9 / 10 | uv, ADRs, docker secrets, 2026-era stack |
| Testing | 7 / 10 | Good parser/client tests; core logic untested |
| Completeness / "wow" | 5.5 / 10 | Single manual snapshot, no visible output |
| Docs & communication | 9 / 10 | ADRs, architecture notes, honest scoping |

### What you did genuinely well

- **Clean layering.** `ingestion/` splits into `clients / parsers / models /
  loaders / jobs`; serving splits into routers. Each layer has one job. This is
  the most important thing a data-eng portfolio must demonstrate, and it is done
  well.
- **Idempotency by design.** Deterministic SHA-256 `observation_id` and
  `status_fingerprint` (`common/ids.py`) feeding `ON CONFLICT DO NOTHING`
  inserts. This is a genuinely senior instinct — most candidates never think
  about re-run safety.
- **Operational metadata.** A `pipeline_runs` table with
  `started / success / failed` states and record counts, wrapped in
  transactions. This is what separates a "script" from a "pipeline".
- **Raw payload retention.** You keep the source JSON, so you can reprocess
  history if your parsing logic changes. Correct medallion-style instinct.
- **You communicate decisions.** ADRs, a source audit with a sample response,
  and a README that honestly fences V1 scope. Reviewers love this.
- **Modern, correct tooling.** uv, ruff, strict mypy (`disallow_untyped_defs`),
  structlog, Python 3.13. Reads like a real 2026 repo, not a tutorial.

### What is holding it back (be honest with yourself)

1. **Most of the project is uncommitted.** Only 4 commits exist, and the entire
   serving layer + DuckDB scripts + their tests are untracked. Your git history
   tells a weaker story than your code does. **Fix this first.**
2. **`torch` is a dependency with zero ML code.** `ml/baselines/` and
   `ml/evaluation/` are empty `__init__.py` files. A ~800MB dependency for
   nothing signals "aspirational, not done."
3. **`tenacity` is declared but never used.** The client re-raises on the first
   timeout. Retry/backoff on a flaky external API is exactly the resilience the
   dependency promises.
4. **Core logic is untested.** The loader (idempotency, upserts, rowcounts) and
   the real analytics SQL have no behavioural tests. Two test files only assert
   that functions exist.
5. **No orchestration.** It is a single manual snapshot. Line status is only
   interesting *over time* — the current design cannot tell you anything a live
   `curl` to TfL could not.
6. **No visible output.** Nothing a non-engineer can look at and understand in
   30 seconds.

---

## 2. What "proper" looks like (the target)

A complete data-engineering + analytics-engineering project demonstrates the
full lifecycle. Use this as your reference architecture and maturity checklist.

```text
                          ┌─────────────────────────────────────────┐
   SOURCE                 │  TfL Line API (live, changes over time)  │
                          └─────────────────────┬───────────────────┘
                                                │
   INGEST        Scheduled Python job (idempotent, retried, observable)
   (EL)                                         │
                                                ▼
   RAW           Postgres  raw.*   ── append-only observations + run metadata
   (source of truth)                            │
                                                ▼
   TRANSFORM     dbt  ── staging → intermediate → marts  (tested, documented)
   (analytics eng)                              │
                                                ▼
   SERVE         DuckDB analytics marts  ──►  FastAPI read-only JSON
                                                │
                                                ▼
   CONSUME       Dashboard (Metabase / small frontend)  +  optional ML / LLM
                                                │
   OPERATE       Orchestrator (cron → Dagster) · CI/CD · tests · monitoring · docs
```

### The maturity checklist

| Capability | Proper project has… | You have… |
|---|---|---|
| **Ingestion** | Scheduled, retried, idempotent, observable | Idempotent ✅ / scheduled ❌ / retried ❌ |
| **Raw storage** | Durable, append-only, run-tracked | ✅ Postgres raw + pipeline_runs |
| **Transformation** | dbt with tests + docs + lineage | ❌ hand-written SQL + shell script |
| **Serving** | Clean API over marts | ✅ FastAPI over DuckDB |
| **Orchestration** | cron/Dagster/Airflow, retries, alerting | ❌ manual |
| **Data quality** | Tests on the data, not just the code | ❌ |
| **CI/CD** | Lint + type + test on every push | ❌ (tools exist, not automated) |
| **Observability** | Structured logs + freshness/quality metrics | 🟡 logs yes, metrics partial |
| **Consumption** | Dashboard or ML that uses the data | ❌ |
| **Docs** | README, ADRs, architecture, runbook | ✅ strong |

You are solid on the left-hand *engineering* column and thin on the right-hand
*value / operations* column. That is exactly the gap to close.

---

## 3. The phased roadmap

Ordered by **impact per unit effort**. Each phase leaves the repo in a shippable,
demonstrable state. Do them in order.

### Phase 0 — Hygiene (½ day) · unblocks everything

- [ ] **Commit everything now**, in logical chunks (serving layer, DuckDB
      scripts, tests). Your best code is currently invisible in git history.
- [ ] **Remove `torch`** until you actually build a model. Don't ship an unused
      800MB dependency.
- [ ] **Wire up `tenacity`** in `TfLLineClient`: retry with exponential backoff
      on timeouts and 5xx. You already declared the dependency — use it.
- [ ] Add a `CONTRIBUTING` / runbook section or a short `docs/runbook.md`
      ("how to run the whole pipeline end to end").

*Outcome: the repo stops undermining itself.*

### Phase 1 — Make it run over time (1–2 days) · the biggest single win

This is what converts "a pipeline" into "an intelligence platform." Your schema
already stores `observed_at` per observation — you just are not accumulating.

- [ ] **Schedule ingestion.** Start with cron or a `docker compose` loop every
      5–10 minutes. Keep the interface clean so you can swap in Dagster later.
- [ ] **Derive reliability metrics** from the accumulating history (these are
      things a snapshot *cannot* produce):
  - minutes-in-disruption per line per day/week
  - per-line uptime % (share of time in "Good Service")
  - disruption *events* via status transitions (good → delayed → good)
  - mean time to recovery
- [ ] Expose these through new API endpoints (`/api/v1/lines/reliability`,
      `/api/v1/lines/{id}/uptime`).

*Outcome: `/history`, DuckDB, and the whole analytics layer become the point of
the project instead of decoration.*

### Phase 2 — Analytics engineering with dbt (2–3 days) · shows the "AE" skill

Right now your transform layer is a shell script and hand-written SQL. dbt is the
industry-standard analytics-engineering tool and its absence is the biggest gap
relative to the project's name.

- [ ] Introduce **dbt** (dbt-duckdb) over your DuckDB marts.
- [ ] Structure models: `staging/` (cleaned raw) → `intermediate/` (reliability
      logic) → `marts/` (what the API reads).
- [ ] Add **dbt tests**: `not_null`, `unique`, `accepted_values` on
      `status_severity`, relationship tests between lines and observations.
- [ ] Add **dbt docs** — the auto-generated lineage graph is a screenshot that
      instantly signals analytics-engineering competence.

*Outcome: you can legitimately claim "analytics engineering" on your CV.*

### Phase 3 — Give it a face (1–2 days) · the recruiter test

A reviewer spends 30 seconds. A screenshot beats 500 lines of clean code they
will not read. Everyone knows the London Underground, so the dataviz sells itself.

- [ ] **Metabase** (or a small single-page frontend) pointed at DuckDB:
  - a live tube-line status board (colour-coded by severity)
  - a reliability leaderboard ("least reliable line this week")
  - an uptime-over-time chart
- [ ] Put a **screenshot at the top of the README.**

*Outcome: the impressive-factor jumps more than any backend work would.*

### Phase 4 — Operate it like production (1–2 days) · shows seniority

- [ ] **CI** (GitHub Actions): run ruff + mypy + pytest on every push; fail the
      build on regressions. Add a green badge to the README.
- [ ] **Data-quality gate:** fail (or alert) if freshness exceeds N minutes or
      if a run inserts 0 rows unexpectedly. You already have
      `pipeline_freshness` — enforce it.
- [ ] **Deploy live** to Fly.io / Railway (API + scheduled ingester). "Here is
      the live endpoint" >> "clone and run docker compose."

### Phase 5 — The differentiated "intelligence" (optional, high ceiling)

You scaffolded two ambitious ideas — pick **one** and finish it rather than
leaving both as stubs.

- [ ] **Forecasting:** probability a line is disrupted at 8am tomorrow given
      day-of-week and history. Start with a *statistical baseline* — it beats an
      empty `torch` dependency and proves you know to baseline before deep
      learning.
- [ ] **Review theme-tagging:** the reviews/NLP angle you scaffolded
      (`reviews/`) is your most differentiated concept. An LLM or rule-based
      pass clustering passenger complaints into themes would stand out.

---

## 4. Testing strategy (dedicated, because it is a named weak spot)

Your suite has a **quality gradient**: the parser tests (113 lines) and client
tests (`respx`) are genuinely good; the rest is thin or hollow.

### Fix first

1. **Delete or replace the two "smoke" tests** — `test_postgres_loader_sql.py`
   and `test_ingestion_job_imports.py` only assert `callable(...)`. They pass
   even if every function body is broken, and they read as padding to a reviewer.
2. **Test the loader for real** (biggest win). Use `testcontainers[postgres]` or
   a session-scoped fixture over docker-compose Postgres:
   - insert N observations → count == N
   - insert the **same batch twice** → second call inserts 0 (proves your
     fingerprint/ID design actually works — this is the payoff for all that
     idempotency effort)
   - severity upsert: re-insert with a changed description → updated, not duplicated
3. **Test the real analytics SQL, not a copy.** In `tests/serving/conftest.py`
   the analytics tables are built with SQL retyped inline. Point the fixture at
   the actual `sql/duckdb/*.sql` files so a bug in production SQL fails a test.
4. **Cover the failure path** — make the client raise and assert the run row
   ends in `failed`. Failure-handling tests read as senior.

### Then raise the floor

- **Enforce coverage:** you already depend on `pytest-cov` but do not use it.
  Add `--cov=tfl_intel --cov-fail-under=80` to `[tool.pytest.ini_options]` and
  put the number in the README.
- **Split tiers:** mark DB/container tests `@pytest.mark.integration` so
  `pytest -m "not integration"` stays fast and CI runs the full set. Shows you
  understand the unit/integration boundary.
- **One property-based test** (`hypothesis`) on `make_status_fingerprint`: same
  inputs → same hash; any field change → different hash. Cheap; shows range.
- **Add dbt tests** (Phase 2) — testing the *data*, not just the code, is the
  analytics-engineering signal reviewers look for.

*Doing the "fix first" list roughly doubles meaningful coverage and moves the
testing score from ~7 to ~9 without much added volume.*

---

## 5. Skills this project can demonstrate (target state)

Frame it this way on your CV / in the README once you reach it:

| Skill area | Evidence in the project |
|---|---|
| Data ingestion | Idempotent, retried, scheduled EL from a live API |
| Data modelling | Raw → staging → marts, deterministic keys, SCD-style history |
| Analytics engineering | dbt models + tests + docs + lineage |
| SQL | Window functions for uptime/transitions, aggregations |
| API design | Read-only FastAPI serving layer over marts |
| Orchestration | Scheduled pipeline with run tracking + freshness SLAs |
| Testing | Unit + integration + data-quality, enforced coverage |
| DevOps | Docker, secrets, CI/CD, cloud deploy |
| Communication | ADRs, architecture docs, dashboard, README |

---

## 6. Suggested order of attack (TL;DR)

1. **Phase 0** — commit everything, drop torch, wire tenacity. *(today)*
2. **Phase 1** — schedule ingestion + reliability metrics. *(the big one)*
3. **Testing "fix first"** — loader idempotency test + real-SQL fixture.
4. **Phase 3** — one dashboard screenshot in the README.
5. **Phase 2** — dbt.
6. **Phase 4** — CI + deploy live.
7. **Phase 5** — one finished "intelligence" feature.

Your foundation is a 9; your payoff is a 5. Nothing above requires
rearchitecting — it requires letting the pipeline *run over time* and *showing
the result*. Ship Phases 1 and 3 and this becomes a portfolio project that
stands out.
