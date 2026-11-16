{% docs reliability_semantics %}

`observed_uptime_pct` is the share of canonical five-minute observations whose
normalized status is `Good Service`. It is an analytical estimate, not an
official TfL availability or SLA measure.

Rules:

- Multiple statuses in one API response resolve to the worst status.
- Multiple runs in one five-minute bucket resolve to the latest run.
- Every canonical poll represents at most five observed minutes.
- A gap over ten minutes breaks disruption continuity; missing time is unknown
  and never silently counted as uptime or disruption.
- Planned closures remain disruptions because the source reports the passenger
  experience as unavailable or degraded. They can be segmented later when a
  reliable planned/unplanned indicator is available.
- Daily coverage is reliable from 90%, provisional from 70%, and insufficient
  below 70%. The denominator is the number of five-minute buckets between
  Europe/London midnights: normally 288, but 276 or 300 on clock-change days.
  Seven-day coverage uses the same thresholds over all buckets in the local
  seven-calendar-day window, including days with no observations.
- Rankings are directional whenever their coverage is not `reliable`.

Model grains and keys:

| Model | Grain / key | Meaning |
|---|---|---|
| `raw.tfl_line_status_observations` | One status item per ingestion run; `observation_id` | Preserves raw source response and both source and observation timestamps. |
| `intermediate.line_status_per_poll` | One selected status per `line_id, observation_bucket` | Worst status per line/run, then latest run in a five-minute bucket. |
| `analytics.dim_line` | One row per `line_id` | Current reference attributes with observed fallback, not Type 2 history. |
| `analytics.dim_status_severity` | One row per `severity_level` | Current reference description; mode-specific severity meanings must be audited before treating this as universally conformed. |
| `analytics.disruption_events` | One observed episode per `disruption_event_id` | A gap over ten minutes breaks continuity; an open event has no recovery duration. |
| `analytics.line_reliability_daily` | One `service_date, line_id` | Sample-based uptime and full-local-day collection coverage. |
| `analytics.line_reliability_rolling_7d` | One `window_end_date, line_id` | Seven local calendar days, including unobserved days in the denominator. |
| `analytics.line_disruption_hourly` | One `service_date, line_id, hour_of_day` | Canonical samples by Europe/London hour. Both occurrences of the autumn clock-change hour share a row. |

TfL status `created`/`modified` is source event time; `observed_at` is when
this pipeline polled the source. Marts use observation time because a current
status response cannot recover states missed between polls. Postgres JSONB is
the raw system of record; DuckDB tables are rebuildable columnar copies. This
is neither log-based CDC nor a lakehouse.

`analytics.pipeline_freshness` stores the latest ingestion timestamps, not a
frozen age. The API and validation query calculate
`minutes_since_latest_success` at read time, so it advances when polling
stops. This is the latest *ingestion* run included in the DuckDB snapshot, not
a separate BI publication timestamp. The Postgres BI copy is refreshed after
each successful validation.

The Metabase trip-time question groups this hourly mart over the previous 90
**complete** local days. Its denominator is the expected five-minute slots in
those hours, including missing and repeated daylight-saving hours. The
disruption percentage is conditional on collected samples; it is not the
probability that a future trip will be disrupted. Sparse coverage remains
insufficient or provisional rather than being filled with Good Service.

{% enddocs %}
