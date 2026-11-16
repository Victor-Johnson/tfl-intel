# TfL Intel: four-day capstone work plan

Use this as a working checklist, not a claim that the project is already
production-ready. Source: a locally supplied TfL guidelines PDF, a
DataExpert concept carousel. This copy contains only slides 1-5 of 10. It is
not an assessment rubric, and listing a concept does not make that technology
necessary for this workload. The broader release criteria remain in the
[capstone checklist](capstone-checklist.md).
The [2026-10-28 execution record](capstone-execution-2026-10-28.md) separates
locally verified work from remaining release work.

**Who is this for?** A transport analyst or curious rider should be able to
answer: Which lines are disrupted now? When are disruptions most often
*observed*? Which line comparisons have enough collected data to trust? The
product's estimates come from periodic TfL status samples, not train movement,
passenger counts, or TfL's official service-level measure.

**Architecture to preserve:** TfL HTTP API -> Postgres raw -> DuckDB/dbt marts
-> FastAPI/public dashboard; validated marts -> Postgres `analytics` ->
Metabase. This is scheduled micro-batch polling, not source streaming. The
five-minute interval gives at most one observation per line per poll bucket;
events shorter than the interval can be missed.

## Current assessment against the supplied slides

Legend: **Implemented** means code exists; **partial** means the relevant path
exists but an important case or proof is missing; **not applicable now** means
there is no current scale or source requirement for it. None of these labels
means the deployment has been verified.

| Slide / concept | Current evidence | Next decision or gap |
|---|---|---|
| Ingestion: batch vs streaming; full vs incremental | **Implemented.** `airflow/dags/tfl_line_status_pipeline.py` schedules five-minute polls; `ingest_line_status.py` appends observations per run. DuckDB refresh replaces raw snapshot tables and dbt rebuilds marts. | Document this as append-only raw micro-batch plus full analytical rebuild. Measure refresh duration before adding incremental models. No Kafka is needed for an HTTP polling source. |
| Ingestion: CDC | **Not applicable to TfL HTTP.** The endpoint returns current state, not a database change log. Source `created`, `modified`, and validity fields are retained in raw rows. | Explain that polling creates an *observed change history*, not lossless CDC. If another database becomes a source, evaluate log-based CDC then. Do not reconstruct missed five-minute states from `modified`. |
| Ingestion: API limits and retry | **Implemented, locally tested.** `tfl_client.py` retries timeouts, 429, and 5xx up to three times, with bounded `Retry-After`; other 4xx are permanent. | The 429 path is covered by `respx`, not a live TfL rate-limit event. Continue to record total requests including retries/reference-data jobs; do not hard-code an assumed entitlement. TfL currently documents 50 anonymous and 500 subscribed requests/minute [here](https://api-portal.tfl.gov.uk/products). |
| Ingestion: schema inference and serialization | **Implemented by explicit contract, not inference.** `line_status_parser.py` and the Pydantic model select fields; Postgres stores the source JSON as `JSONB`. | Prefer this to auto-inference for a small API. Add fixtures for new/missing optional fields, malformed required fields, and multiple validity periods. Preserve the full payload; document that only the first validity period is currently promoted to columns. |
| Ingestion: idempotency | **Partial.** `make_observation_id` plus `ON CONFLICT DO NOTHING` deduplicates within an `ingestion_run_id`. A new run ID is generated for every invocation, so retrying a whole poll as a new run records another observation. | Decide whether the contract is "one snapshot per attempt" or "one snapshot per scheduled bucket." Test same-run replay and new-run repeat separately. For strict scheduled-bucket idempotency, derive a stable batch key from mode + scheduled interval and keep an attempt ID separately; don't dedupe unchanged status across different real polls. |
| Ingestion: late arrivals and bad records | **Partial.** `observed_at` is captured at poll start; source timestamps are retained, but marts use observation time. `raw.invalid_records` exists without a loader path. | Define event time versus observation time. A delayed response belongs to its actual request time, not to a fabricated past service state. Test delayed/older source timestamps and out-of-order manual polls. Decide whether one malformed status fails the whole poll or is quarantined; implement the chosen rule and reconcile `records_rejected`. Empty 200 responses should be treated as suspicious and surfaced. |
| Modeling: facts/dimensions and star schema | **Implemented in spirit.** `dim_line`, `dim_status_severity`, `fct_disruption_events`, daily and rolling reliability marts exist. Raw Postgres is normalized enough for ingestion; analytics is denormalized for questions. | Write down grain, keys, and join direction for each mart in `dbt/models/metrics.md`; prove one number back to a raw payload. Avoid introducing a snowflake model solely to check a box. |
| Modeling: SCD, partitioning, clustering, lakehouse, compaction | **Not needed yet.** The line dimension represents current/reference metadata, not a Type 2 history; Postgres indexes exist. DuckDB is columnar, but the system is not a lakehouse. Local-day DST coverage is now tested. | Keep historical status observations in the fact. Add SCD2 only if a changed line name/mode must be queried as-of time. Consider date partitioning/Parquet only after measured storage or refresh pain; then specify late-data rewrite and compaction rules. Do not call normal Postgres indexing "clustering." |
| Distributed processing: shuffle, skew, broadcast/sort-merge joins, AQE | **Not applicable now.** DuckDB/dbt runs on one host; those are primarily distributed-engine concerns. | Do not add Spark to manufacture scale. Measure row counts, runtime, peak memory, and a representative query plan (`EXPLAIN ANALYZE`). Investigate skew if one line/status dominates a join. Explain predicate pushdown, bounded queries, local parallelism, and spill only when measurements make them relevant. |
| Orchestration/reliability: DAGs, retries, recovery | **Partial.** Airflow has dependencies, two retries, `catchup=False`, and `max_active_runs=1`; dbt and runtime validation precede BI publication. | Test timeout, parser failure, database outage, validation failure, and a rerun. Airflow's retry of `ingest_line_status` creates a fresh run ID: document or change that semantics. Add an external alert for repeated failures. Airflow recommends retry-safe task outcomes [here](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html). |
| Orchestration/reliability: backfill, freshness, SLA | **Partial.** `analytics.pipeline_freshness`, `/ready`, and the dashboard show freshness; no true historical source backfill is possible from a current-state endpoint. | Separate raw poll age, published snapshot age, and end-to-end latency. Set a measured freshness target, e.g. <=15 minutes in normal operation, and alert on a breach. Rebuilding DuckDB/dbt from retained Postgres history is a *replay*, not recovery of missed source states. Test recovery after a failed publish. |

## Layer-by-layer implementation guide

### Data modeling and storage: make the grain provable

- [ ] **Fact grain:** `raw.tfl_line_status_observations` is one status item in
      one ingestion run; `int_line_status_per_poll` is one selected status per
      line/five-minute bucket; `fct_disruption_events` is one observed episode.
      Write those contracts next to the models in `dbt/models/metrics.md`.
      Add dbt uniqueness tests for `(line_id, observation_bucket)` and
      `(service_date, line_id)` where appropriate; existing singular tests
      cover some grains, so inspect them before duplicating work.
- [ ] **Dimensions and history:** inspect `dim_line.sql` and
      `dim_status_severity.sql`. Both resolve to current/latest metadata; they
      are not SCD Type 2. Check whether severity descriptions differ by mode
      before trusting `severity_level` as a global dimension key. If historical
      line-name/mode changes matter, model effective dates and an as-of join;
      otherwise document current attributes as a deliberate simplification.
- [ ] **Storage and physical design:** Postgres retains raw JSONB and has
      indexes in `sql/postgres/03_create_indexes.sql`; DuckDB holds columnar
      copies and dbt table marts. Measure table sizes and the queries that use
      each index. `EXPLAIN` a raw time-range lookup and a serving query before
      adding composite indexes, partitioning, or a Parquet layer. Indexes cost
      ingest writes and space; a full DuckDB copy costs refresh time but is
      easy to rebuild. Neither makes this a lakehouse.
- [ ] **Data quality:** test missing polls, duplicate runs, clock changes,
      multiple statuses, and unresolved events. The denominator and event
      rules in `mart_line_reliability_daily.sql` and
      `fct_disruption_events.sql` are part of the product contract, not only
      SQL implementation detail. Assert both the answer and the coverage
      quality label.

### Processing and scale: prove the single-host choice

- [ ] **Baseline:** use Airflow task timings, row counts, DuckDB file size,
      memory use, and `EXPLAIN ANALYZE` for a representative mart query. Compare
      full refresh duration to the five-minute schedule and check whether runs
      are skipped or queued (`max_active_runs=1`). Save the query and results.
- [ ] **Join and filter behavior:** inspect the `dim_line` full outer join,
      the per-poll window sort, and the rolling seven-day model. Determine
      which operators dominate time or memory. Filter on a bounded date/window
      in serving queries and verify the plan actually reads fewer rows; do not
      claim predicate pushdown based only on SQL syntax.
- [ ] **Skew and parallelism:** count observations by line, mode, and status;
      compare largest group with the median. On this host, DuckDB can run work
      in parallel, but there is no network shuffle, broadcast join, Spark AQE,
      or distributed partition pruning to tune. Document those as out of
      scope, not implemented. Try a lower DuckDB memory limit on a disposable
      copy to observe whether a query spills or fails, if performance learning
      is the goal.
- [ ] **Scale decision:** keep full rebuild if it finishes comfortably before
      the next poll and readers remain available. Only then consider an
      incremental raw snapshot or partitioned Parquet. That path must handle
      late rows, replay, merge keys, and small-file compaction; complexity is
      justified by a measured bottleneck, not by a slide heading.

### Orchestration and scheduling: make failure recoverable

- [ ] **DAG contract:** inspect both files in `airflow/dags`. Status polls run
      every five minutes; reference data runs daily. Draw the task dependency
      graph, expected inputs/outputs, retry owner (HTTP versus Airflow),
      `catchup=False`, and `max_active_runs=1`. Explain what a missed scheduled
      poll means: this current-state API cannot backfill its lost state.
- [ ] **Retry and replay:** inject timeout, 429, parser failure, Postgres
      outage, and dbt validation failure. Check task state, `pipeline_runs`,
      observation count, and published version after each. Airflow retries the
      ingestion shell task from scratch; it does not reuse the random run ID.
      Update the misleading "re-runs are no-ops" statement in `docs/runbook.md`
      after choosing the actual replay contract.
- [ ] **Publication order:** the status DAG runs dbt validation before BI
      publication, but checks API readiness *after* publishing BI. Verify
      whether the API can read during the DuckDB write and whether a ready
      check can fail after BI has advanced. If so, validate a separate DuckDB
      candidate, make it available atomically, check readiness, then publish
      BI from that validated version or document a safe rollback procedure.
- [ ] **Freshness and alerts:** distinguish latest successful TfL poll,
      latest successfully published DuckDB/BI version, and API read freshness.
      `analytics.pipeline_freshness` currently derives from ingestion run
      timestamps, so it cannot alone prove a successful publish. Record a
      publication timestamp/version, define an end-to-end target, and test an
      alert for repeated failures or stale served data.

### Important modeling caveat

`mart_line_reliability_daily.sql` now uses 288 expected five-minute buckets on
an ordinary local day and 276 or 300 on Europe/London clock-change days.
This remains **full-day collection coverage**, not operating-hours coverage.
The CI fixture tests both transition denominators and the seven-day window.
The current `int_line_status_per_poll.sql` selects the worst reported status
per line/run and then the latest run per line/bucket; this rule also deserves
a multi-status fixture.

## Four days to a convincing demonstration

Budget roughly one focused working day per section. Finish a small verified
slice before moving on. For every completed box, save the command, result,
date, and Git commit in a local evidence note; never save credentials.
Boxes marked **Stretch** are valuable but can move to the release checklist
without weakening the four-day learning outcome.

### Day 1: prove ingestion semantics

- [ ] Read `src/tfl_intel/ingestion/clients/tfl_client.py`,
      `jobs/ingest_line_status.py`, `parsers/line_status_parser.py`, and
      `loaders/postgres_loader.py`; draw the request -> parse -> transaction ->
      run-state path in your own words.
- [x] Add focused `respx` tests in `tests/ingestion/test_tfl_client.py` for
      429 with/without `Retry-After`, timeout, and exhausted retries. Implement
      bounded 429 behavior in `_is_retryable`/`_send`; never retry arbitrary
      4xx. Verify a 429 eventually marks the run failed in a job/integration
      test.
- [x] Add parser/job fixtures for missing optional fields, two statuses for
      one line, bad required fields, an empty response, and late source
      timestamps. For this pass, fail the whole poll on a malformed required
      field and record the failure clearly; don't silently count it as success.
- [ ] **Stretch:** implement per-record quarantine in `raw.invalid_records`
      and reconcile `records_rejected` if partial-poll availability matters.
- [x] Run `uv run pytest tests/ingestion -v` and a local poll. In Postgres,
      compare `raw.pipeline_runs.records_received/inserted/rejected` with
      observation counts for that run. Repeat one batch and confirm the
      documented idempotency contract.

**Done when:** the same-run replay result, new-run result, 429 outcome, empty
response outcome, and one malformed-record outcome are reproducible from tests
or saved queries. If time is short, finish these before adding a new source.

### Day 2: make analytical numbers trustworthy

- [x] Trace a raw observation through `raw_snapshot`,
      `int_line_status_per_poll`, `fct_disruption_events`, and
      `mart_line_reliability_daily`. Record the grain and key of each table in
      `dbt/models/metrics.md`.
- [x] Extend `scripts/create_dbt_ci_fixture.py` with a small timeline: Good
      Service -> delay -> recovery, duplicate poll, missed poll, two statuses
      in one response, and a Europe/London clock-change day. Add dbt or Python
      assertions for observed uptime, coverage, episode count, and duration.
- [x] Fix or explicitly scope the 288-bucket local-day denominator. Prefer a
      tested per-date expected-bucket calculation; if postponing it, label
      transition dates as not comparable and do not rank them.
- [x] Run `make dbt-ci` and `make validate-marts` against a refreshed local
      database. Check that low-coverage periods are flagged, never filled in
      as Good Service.

**Done when:** you can explain why a chosen line's uptime and coverage have
those exact numerators and denominators, including a missing poll.

### Day 3: processing performance and publication safety

- [ ] Time each Airflow stage: HTTP ingestion, Postgres -> DuckDB snapshot,
      dbt build, validation, BI publication, and API read. Record row counts,
      file size, peak memory, and p50/p95 API response times from repeated
      local requests. No synthetic claim of distributed scale.
- [ ] Run `EXPLAIN ANALYZE` on one expensive model/query and check group-size
      skew. Write a one-page decision: why single-host DuckDB is enough now,
      what measured threshold would justify partitioning, incremental builds,
      or a distributed engine.
- [x] Test API reads while a refresh writes DuckDB. If readers lock or see a
      partial build, build/validate a replacement file and switch publication
      only after success. DuckDB's process-level concurrency constraints are
      documented [here](https://duckdb.org/docs/current/connect/concurrency).
- [ ] Decide whether full rebuild meets the five-minute schedule. If it does,
      keep it. If it does not, prototype an incremental snapshot on a copy,
      including a late-arrival replay test and a full-rebuild recovery path.

**Done when:** you have a measured refresh budget, a query plan, a live-read
refresh test, and a written full-versus-incremental/distributed decision.

### Day 4: orchestration, BI, and a reproducible demo

- [ ] Draw and run both Airflow DAGs. Force a source failure and a dbt test
      failure; confirm task order, bounded retries, no BI publish after failed
      validation, and a clean recovery. Check the five-minute cadence does
      not queue unfinished runs indefinitely.
- [ ] Compare `raw.pipeline_runs`, the DuckDB freshness mart, and the BI
      publication state after those failures. Add a publish timestamp/version
      or explicitly label the current endpoint as ingestion freshness only.
- [ ] **Stretch:** configure one external alert destination; trigger and clear
      it in a test before calling the deployment production-ready.

- [ ] Choose **Metabase** for this pass: `docker-compose.metabase.yml`, the
      restricted `metabase_reader`, publication code, and a private seven-card
      traveler dashboard now exist. Superset is a valid alternative for richer BI control,
      but switching now adds setup, security, and maintenance work without a
      demonstrated user need. Follow `docs/metabase/README.md`; verify the
      reader cannot select `raw` and that only the intended dashboard is
      public. Metabase public links are accessible without login [here](https://www.metabase.com/docs/latest/embedding/public-links).
- [ ] Build the dashboard around decisions, not chart variety. Keep each
      chart's time window and observation coverage visible. See the questions
      below; start from the versioned SQL and improve only where the decision
      requires it.
- [ ] From a clean checkout, run `make check`, `make production-config`, and
      the `docs/runbook.md` path. Save the tested commit and any failures.
- [ ] **Stretch if the target host is ready:** follow `DEPLOYMENT.md`; run
      external smoke checks, verify HTTPS and restricted Postgres/Airflow,
      then rehearse backup restore and rollback. Do not claim deployment until
      these checks pass.
- [ ] Update `PORTFOLIO.md` with a five-minute demo: user question, live or
      explicitly labeled fixture data, one traced metric, a failed-run
      recovery, measured freshness, architecture tradeoffs, and known limits.

**Done when:** another person can find a currently affected line, see whether
the data is fresh, compare lines without mistaking sparse coverage for good
service, and reproduce your evidence.

The checked items above were verified in the isolated local environment; see
the [execution record](capstone-execution-2026-10-28.md) and
[metric trace](metric-lineage-example.md). Unchecked items are still work,
especially performance over sustained history, alerts, credential-safe BI,
external deployment, and user verification. The four days describe an
implementation sequence, not elapsed evidence of four days of operation.

## Dashboard questions worth answering

| User question | Visual / source | Useful decision and guardrail |
|---|---|---|
| What is disrupted now, and why? | Current-line table from `analytics.current_line_status`; line, mode, severity, reason, observed time | Locate an affected line quickly. Mark a snapshot stale; do not imply an unobserved change was live. |
| Which lines have the most observed disruption? | Seven-day line bars from `line_reliability_rolling_7d` | Compare lines only above a coverage threshold; show coverage beside uptime. Planned closures are currently included. |
| Are disruptions concentrated at certain hours? | Weekday/hour heatmap from `network_disruption_hourly` | Help an analyst prioritize investigation. Show sample count or filter thin cells; this is observed status frequency, not passenger impact. |
| Is the network getting better or did collection fail? | Daily uptime and coverage trend, plus latest raw and published timestamps | Distinguish a genuine change from missing polls or a stuck publisher. |
| How long do observed disruption episodes last? | Recent-event table from `disruption_events`, with resolved flag and observed minutes | Inspect incidents; never show an open event as a completed recovery time. |
| Which modes deserve follow-up? | Mode reliability table with weighted uptime, coverage, event count | Prioritize investigation, not promise faster journeys; compare like-for-like windows. |

The existing Metabase questions cover most of this. The important enhancement
is *context*: include coverage, counts, last refresh, window, and the
planned-work caveat. A heatmap with only a high percentage and three samples
is more misleading than useful.

## After the four days

- [ ] Collect the 30 days of live history required by `docs/project-charter.md`;
      a four-day build cannot create honest 30-day evidence. Publish a
      coverage report and measured latency/cost over that period.
- [ ] Add planned-work/timetable data only when you can define a defensible
      operating-hours denominator and planned-versus-unplanned split.
- [ ] Revisit SCD2, partitioning, Parquet compaction, or distributed processing
      only after a specific query, retention, or refresh limit is measured.
