# TfL Intel: capstone delivery checklist

**Scope:** A single-host deployment that collects TfL line status, preserves
raw observations, builds tested reliability models, and serves results through
an API and dashboard. The intended host and proxy are described in
[DEPLOYMENT.md](../DEPLOYMENT.md).

**Product question:** Which lines are disrupted now, how has their observed
status changed, and how much of the expected observation history was actually
collected? Reliability in this project is an estimate from periodic samples,
not an official TfL service-level measure.

The [2026-10-28 execution record](capstone-execution-2026-10-28.md) lists
verified local checks and remaining release work. It does not close the gates
below by itself.

The repository already contains ingestion, Postgres, DuckDB, dbt, Airflow,
FastAPI, a dashboard, CI, and deployment scripts. A file or test in the repo is
evidence of implementation, not evidence that the deployed system works. Keep
the boxes below open until the stated checks pass. For each check, record the
date, Git commit, environment, command or query, result, and any exception in a
small evidence log. Do not include credentials or API keys.

## Gate 1: a safe first deployment

Complete this gate before presenting the public dashboard as live.

### 1. Reproduce the complete path

- [ ] From a clean checkout, follow [the runbook](runbook.md): initialize
      Postgres, ingest reference and status data, refresh DuckDB and dbt, run
      mart validation, start the API, and load `/dashboard` and `/docs`.
- [ ] Run `make check` and the Postgres integration tests. Save the outputs and
      the commit tested. Fix failures or document a deliberate exception.
- [ ] Show at least one observation from each configured mode in raw Postgres,
      the corresponding DuckDB snapshot, and a serving endpoint. A successful
      HTTP response with no records is not sufficient.
- [ ] Trace one dashboard value back through its dbt mart, intermediate row,
      raw observation, ingestion run, and preserved source payload. Save the
      query and the explanation. The isolated API example is in
      [the metric trace](metric-lineage-example.md); verify the rendered
      dashboard value against it before release.

**Decision:** Keep the existing batch path while it meets the required
freshness. A polled source does not gain value from Kafka simply because the
pipeline has multiple stages.

### 2. Establish a data contract

- [ ] State the grain and primary key of every raw, intermediate, and mart
      table in [the metric definitions](../dbt/models/metrics.md). Document
      timestamp timezone, poll bucket, tie breakers, and multiple statuses per
      line.
- [ ] Build fixture timelines for a normal service, disruption, recovery,
      duplicate replay, missing poll, long gap, simultaneous statuses, and a
      daylight-saving transition. Assert expected uptime, coverage, episode
      count, and duration.
- [ ] Confirm missing polls reduce coverage rather than becoming Good Service.
      Verify the API and dashboard show the coverage label beside each uptime
      estimate and do not rank sparse histories as reliable.
- [ ] Label the current 288 expected five-minute buckets per day as **full-day
      collection coverage**. Do not describe it as operating-hours coverage
      until timetable data supports that denominator. Check whether local
      daylight-saving days require 276 or 300 buckets instead.
- [ ] Check a few records against TfL responses. Document what a sampled
      status can and cannot establish about actual train service.

**Decision:** The V1 rule treats a non-Good-Service status as disrupted. This
is reproducible, but it can include planned closures. Keep the distinction
visible in the product; add a planned-work source only after defining and
testing how it changes historical metrics.

### 3. Prove retries and publication safety

- [x] Replay a fixed batch and prove it creates no duplicate observations.
      Then run a new poll and prove it creates a new ingestion run and the
      expected observations. Verified against isolated Postgres; this is
      same-run idempotency, not deduplication across different poll runs.
- [ ] Inject an API timeout and a SQL failure after a run row is created.
      Confirm each marks the run failed, retries stop at the configured bound,
      and no partial batch is reported as successful. Separately stop Postgres
      before connection: no run row can be written, so confirm Airflow and the
      external alert expose that outage.
- [ ] Interrupt DuckDB/dbt refresh while the API is serving requests. Verify
      readers receive the previous complete snapshot or a clear unavailable
      response. If they see lock errors or partial data, publish a validated
      replacement file atomically before production use.
- [ ] Start both Airflow DAGs and inspect task order, retries, `max_active_runs`,
      and one failed-run recovery. Confirm a failed validation prevents BI
      publication.
- [ ] Observe at least a day of scheduled runs. Record successful/expected
      polls, latest raw success age, latest published snapshot age, and the
      longest refresh time. Target no more than 15 minutes of data age during
      normal operation; treat raw and served freshness as separate signals.

**Decision:** Five-minute polling can miss shorter disruptions. Faster polling
improves resolution but increases requests, storage, and rebuild pressure.
Airflow adds run history and dependency control at the cost of memory and
operational complexity. Revisit either choice when measured failures or user
needs warrant it. Airflow's [best practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
emphasize retry-safe tasks.

### 4. Secure and operate the deployed service

- [ ] Deploy the tested commit using [the deployment guide](../DEPLOYMENT.md).
      Verify HTTPS and public routes from outside the VPS. Confirm Postgres and
      Airflow cannot be reached from the public internet.
- [ ] Confirm the API container has no Postgres credentials and its DuckDB
      mount is read-only. Verify `.env` and secret files are excluded from Git
      and no key appears in request, task, or proxy logs.
- [ ] Confirm `/health` reports process health, while `/ready` detects missing
      or invalid analytical data. Bound API limits and error responses; test a
      missing line, invalid `limit`, empty result, and stale snapshot.
- [ ] Connect an alert destination for repeated ingestion failures and stale
      *served* data. Trigger both alerts in a controlled test and record how
      they clear. A dashboard warning alone is not an operational alert.
- [ ] Restore a backup into an isolated Postgres instance, rebuild DuckDB, and
      compare representative counts and API results. Record measured recovery
      time and potential data loss, then decide whether the backup interval is
      acceptable. Keep an off-host copy.
- [ ] Verify the daily backup job completes a full disposable restore before
      pruning operational raw history older than 90 days. Confirm recent rows
      survive, old rows disappear from the next DuckDB/BI refresh, and backup
      rotation/off-host retention match the intended data policy.
- [ ] Deploy a small change, run external smoke checks, and rehearse rollback
      without deleting persistent volumes. Record CPU, memory, disk use, API
      latency, and refresh time during the exercise.

**Decision:** One VPS keeps cost and deployment simple but creates one failure
domain. Postgres retains durable raw evidence; DuckDB is a rebuildable read
model. That boundary costs storage and refresh time. DuckDB's
[concurrency model](https://duckdb.org/docs/current/connect/concurrency)
makes the refresh/read test essential. Compose
[secrets](https://docs.docker.com/reference/compose-file/secrets/) restrict
which services receive each credential.

### 5. Validate the user experience

- [ ] Have a person unfamiliar with the project find the current disruption,
      select a line and planned weekday/hour in Metabase, compare its observed
      disruption share with collection coverage, and inspect recent history
      without help. Ask whether they mistake the chart for a forecast; fix the
      most consequential misunderstanding they encounter.
      Fix the most consequential misunderstanding they encounter.
- [ ] Make current status, stale data, missing observations, and API failure
      visibly different states. Check mobile width, keyboard access, loading,
      empty responses, and long reason text.
- [ ] Document endpoint fields, units, timezones, nulls, limits, and metric
      caveats in the API schema and dashboard text. Show TfL attribution.

**Decision:** The custom dashboard and Metabase traveler view are two surfaces
over the same tested marts. Metabase adds another database, access control,
and maintenance. The local traveler view has been provisioned with fixture
data, but production sharing remains a separate security and user test.

## Gate 2: a defensible capstone

Complete this gate before calling the project finished.

- [ ] Collect the 30 days of live history targeted in
      [the project charter](project-charter.md). Report coverage for every mode
      and evaluate rolling seven-day windows. Label low-coverage rankings as
      provisional; do not manufacture history with fixtures.
- [ ] Publish a short evidence summary: expected versus successful polls,
      median and worst refresh time, API response time, latest data age, backup
      restore time, and measured operating cost. Include dates and the sample
      window for every number.
- [ ] Demonstrate at least one failure and recovery: source timeout, missed
      poll, failed model validation, or interrupted refresh. Show the effect on
      pipeline runs, alerting, and the dashboard.
- [ ] Show a clean CI run that covers Python checks, Postgres integration,
      dbt build/tests, Compose validation, and deployable images. Link the
      passing run and tested commit in [PORTFOLIO.md](../PORTFOLIO.md).
- [ ] Write the case study around a user question, the data contract, lineage,
      reliability assumptions, deployment, measured results, and what failed.
      Include a reproducible demo and label fixture versus live data.
- [ ] For each major technology choice, keep a short decision record: options,
      constraint, measurement, decision, downside, and trigger to revisit it.
      Cover polling interval, Postgres, DuckDB, dbt, Airflow, FastAPI, Metabase,
      and the single VPS.

## Extensions after the capstone

Choose an extension because it answers a missing question or removes a measured
bottleneck. Do not add all of these by default.

| Candidate | Benefit | Cost or risk | Start when |
|---|---|---|---|
| Timetable and planned-work data | Better coverage denominator and planned/unplanned distinction | New source contracts and historical joins | Users need operating-hours or unplanned-only comparisons |
| Incremental DuckDB build | Shorter refreshes | Harder replay, backfill, and recovery | Full rebuild approaches the polling interval or affects readers |
| More frequent polling | Better detection of short events | More requests, rows, and refresh work | Sampled gaps change a decision users make |
| Metabase | Flexible analyst exploration | Another service, database, and permissions model | A real user needs ad hoc slicing beyond the product dashboard |
| Forecasting baseline | Potential forward-looking signal | Label scarcity and time leakage | High-coverage history supports a time-based evaluation |
| Cloud warehouse or streaming | More concurrency or throughput | Higher cost and complexity | Measured scale exceeds the single-host design |

For each extension, write a one-page experiment before implementation:
**question, current baseline, candidate design, success metric, failure mode,
and stop condition**. The result should change a decision or simplify the
system; a new tool alone is not a capstone outcome.
