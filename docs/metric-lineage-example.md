# Central line metric lineage: local verification

This is a reproducible example from the isolated `tfl-intel-capstone` test
project on 2026-10-28, after four real TfL status polls. It is not a claim
about a production deployment or a full day of collection.

## Source and ingestion run (Postgres)

```sql
select
    o.observation_id, o.ingestion_run_id, r.status as run_status,
    o.observed_at, o.status_description,
    o.raw_payload -> 'line' ->> 'id' as source_line_id,
    o.raw_payload -> 'line_status' ->> 'statusSeverityDescription'
        as source_status
from raw.tfl_line_status_observations as o
join raw.pipeline_runs as r using (ingestion_run_id)
where o.line_id = 'central'
  and o.observed_at::date = date '2026-10-28'
order by o.observed_at;
```

The four rows had successful run states, preserved source line ID `central`,
and source status `Minor Delays`. Their observation IDs were:

```text
d82eac96ae714a10c071e5c03d4b265d9f518df5c5c6e49f2765121b8b6459a0
abd2d05c16b90c8d6d4a0c63f3ec74bab06977a1569754ec24f7dbdd6fd0e090
90c2d69702faa6be110c86f1bcaa4d9003a03a5af9d1e3b907a3b759c8d2a1b0
7f3b78cdf8270e000bb83de94369239a73489181a6d659b40373dfbbfa150dc7
```

## Snapshot, canonical polls, and marts (DuckDB)

```sql
select count(*) as copied_raw_rows
from raw_snapshot.tfl_line_status_observations
where line_id = 'central'
  and cast(observed_at at time zone 'Europe/London' as date)
      = date '2026-10-28';

select observation_id, observation_bucket, status_description, is_disrupted
from intermediate.line_status_per_poll
where line_id = 'central'
  and cast(observed_at at time zone 'Europe/London' as date)
      = date '2026-10-28'
order by observed_at;

select event_started_at, event_ended_at, observation_count, is_resolved
from analytics.disruption_events
where line_id = 'central'
  and cast(event_started_at at time zone 'Europe/London' as date)
      = date '2026-10-28'
order by event_started_at;

select total_observations, good_service_observations,
       disrupted_observations, expected_full_day_observations,
       observed_uptime_pct, full_day_coverage_pct, coverage_quality,
       disruption_event_count
from analytics.line_reliability_daily
where line_id = 'central' and service_date = date '2026-10-28';
```

The intermediate table selected the same four observation IDs, in 15:00,
15:05, 15:10, and 15:35 UTC buckets. The last gap exceeds ten minutes, so
the event model reports **two unresolved episodes**; it does not infer a
recovery or continuous disruption during the gap. The daily mart reports
`total_observations=4`, `good_service_observations=0`,
`disrupted_observations=4`, `expected_full_day_observations=288`,
`observed_uptime_pct=0.0`, `full_day_coverage_pct=1.39`, and
`coverage_quality='insufficient'`. Thus 0/4 is an observed-status fraction,
while 4/288 is full-day **collection coverage**, not TfL service availability.
The API's Central-line daily reliability endpoint returned the same values.
