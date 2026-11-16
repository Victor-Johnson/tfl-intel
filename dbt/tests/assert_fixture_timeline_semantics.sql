{% if env_var('TFL_DBT_CI_FIXTURE', 'false') == 'true' %}
with poll_summary as (
    select
        count(*) as canonical_polls,
        count(*) filter (
            where observation_bucket = timestamptz '2026-07-14 10:05:00+00'
              and status_description = 'Minor Delays'
              and source_status_count = 2
        ) as worst_status_selected,
        count(*) filter (
            where observation_bucket = timestamptz '2026-07-14 10:20:00+00'
              and observation_id = 'timeline-5'
        ) as latest_run_selected
    from {{ ref('int_line_status_per_poll') }}
    where line_id = 'timeline'
),
event_summary as (
    select
        count(*) as episodes,
        count(*) filter (where is_resolved) as resolved_episodes
    from {{ ref('fct_disruption_events') }}
    where line_id = 'timeline'
),
daily as (
    select * from {{ ref('mart_line_reliability_daily') }}
    where line_id = 'timeline'
      and service_date = date '2026-07-14'
)
select daily.line_id
from daily, poll_summary, event_summary
where poll_summary.canonical_polls <> 4
   or poll_summary.worst_status_selected <> 1
   or poll_summary.latest_run_selected <> 1
   or event_summary.episodes <> 2
   or event_summary.resolved_episodes <> 1
   or daily.total_observations <> 4
   or daily.good_service_observations <> 2
   or daily.disrupted_observations <> 2
   or daily.observed_uptime_pct <> 50
   or daily.full_day_coverage_pct <> 1.39
   or daily.coverage_quality <> 'insufficient'
union all
select 'missing timeline day'
where not exists (select 1 from daily)
{% else %}
select 1 where false
{% endif %}
