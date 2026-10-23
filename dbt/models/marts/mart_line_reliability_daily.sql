{{ config(alias='line_reliability_daily') }}

with daily_observations as (
    select
        cast(observed_at at time zone 'Europe/London' as date)
            as service_date,
        line_id,
        max(line_name) as line_name,
        max(coalesce(mode_name, 'unknown')) as mode_name,
        count(*) as total_observations,
        count(*) filter (where not is_disrupted)
            as good_service_observations,
        count(*) filter (where is_disrupted) as disrupted_observations,
        count(*) filter (
            where normalized_status_description = 'minor delays'
        ) as minor_delay_observations,
        count(*) filter (
            where normalized_status_description = 'severe delays'
        ) as severe_delay_observations,
        count(*) filter (
            where normalized_status_description = 'part suspended'
        ) as part_suspended_observations,
        count(*) filter (
            where normalized_status_description = 'service closed'
        ) as service_closed_observations,
        min(observed_at) as first_observed_at,
        max(observed_at) as last_observed_at
    from {{ ref('int_line_status_per_poll') }}
    group by service_date, line_id
),
daily_events as (
    select
        cast(event_started_at at time zone 'Europe/London' as date)
            as service_date,
        line_id,
        count(*) as disruption_event_count,
        count(*) filter (where is_resolved)
            as resolved_disruption_event_count,
        avg(event_duration_minutes) filter (where is_resolved)
            as mean_recovery_minutes
    from {{ ref('fct_disruption_events') }}
    group by service_date, line_id
)
select
    observations.service_date,
    observations.line_id,
    observations.line_name,
    observations.mode_name,
    observations.total_observations,
    observations.good_service_observations,
    observations.disrupted_observations,
    observations.minor_delay_observations,
    observations.severe_delay_observations,
    observations.part_suspended_observations,
    observations.service_closed_observations,
    observations.total_observations * 5 as observed_minutes,
    observations.good_service_observations * 5
        as estimated_good_service_minutes,
    observations.disrupted_observations * 5
        as estimated_disruption_minutes,
    round(
        100.0 * observations.good_service_observations
        / nullif(observations.total_observations, 0),
        2
    ) as observed_uptime_pct,
    288 as expected_full_day_observations,
    round(
        least(100.0, 100.0 * observations.total_observations / 288),
        2
    ) as full_day_coverage_pct,
    case
        when observations.total_observations / 288.0 < 0.70
            then 'insufficient'
        when observations.total_observations / 288.0 < 0.90
            then 'provisional'
        else 'reliable'
    end as coverage_quality,
    coalesce(events.disruption_event_count, 0) as disruption_event_count,
    coalesce(events.resolved_disruption_event_count, 0)
        as resolved_disruption_event_count,
    round(events.mean_recovery_minutes, 2) as mean_recovery_minutes,
    observations.first_observed_at,
    observations.last_observed_at
from daily_observations as observations
left join daily_events as events using (service_date, line_id)
