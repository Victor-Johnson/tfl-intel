{{ config(alias='line_reliability_rolling_7d') }}

with rolling as (
    select
        service_date,
        line_id,
        line_name,
        mode_name,
        sum(total_observations) over reliability_window
            as total_observations_7d,
        sum(good_service_observations) over reliability_window
            as good_service_observations_7d,
        sum(disrupted_observations) over reliability_window
            as disrupted_observations_7d,
        sum(observed_minutes) over reliability_window as observed_minutes_7d,
        sum(estimated_disruption_minutes) over reliability_window
            as estimated_disruption_minutes_7d,
        sum(disruption_event_count) over reliability_window
            as disruption_event_count_7d,
        sum(resolved_disruption_event_count) over reliability_window
            as resolved_disruption_event_count_7d
    from {{ ref('mart_line_reliability_daily') }}
    window reliability_window as (
        partition by line_id
        order by service_date
        range between interval 6 day preceding and current row
    )
),
with_expected as (
    select
        *,
        cast(date_diff(
            'minute',
            cast(service_date - interval 6 day as timestamp)
                at time zone 'Europe/London',
            cast(service_date + interval 1 day as timestamp)
                at time zone 'Europe/London'
        ) / 5 as integer) as expected_full_week_observations
    from rolling
)
select
    service_date as window_end_date,
    cast(service_date - interval 6 day as date) as window_start_date,
    line_id,
    line_name,
    mode_name,
    total_observations_7d,
    good_service_observations_7d,
    disrupted_observations_7d,
    observed_minutes_7d,
    estimated_disruption_minutes_7d,
    disruption_event_count_7d,
    resolved_disruption_event_count_7d,
    expected_full_week_observations,
    round(
        100.0 * good_service_observations_7d
        / nullif(total_observations_7d, 0),
        2
    ) as observed_uptime_pct_7d,
    round(
        least(100.0, 100.0 * total_observations_7d
            / expected_full_week_observations),
        2
    ) as coverage_pct_7d,
    case
        when total_observations_7d / expected_full_week_observations < 0.70
            then 'insufficient'
        when total_observations_7d / expected_full_week_observations < 0.90
            then 'provisional'
        else 'reliable'
    end as coverage_quality_7d,
    dense_rank() over (
        partition by service_date
        order by
            good_service_observations_7d
                / nullif(total_observations_7d, 0),
            line_name
    ) as least_reliable_rank_7d
from with_expected
