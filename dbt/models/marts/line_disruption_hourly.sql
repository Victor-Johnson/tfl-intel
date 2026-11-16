{{ config(materialized='table') }}

with local_polls as (
    select
        line_id,
        line_name,
        coalesce(mode_name, 'unknown') as mode_name,
        observed_at at time zone 'Europe/London' as local_observed_at,
        is_disrupted
    from {{ ref('int_line_status_per_poll') }}
)
select
    cast(local_observed_at as date) as service_date,
    line_id,
    max(line_name) as line_name,
    max(mode_name) as mode_name,
    cast(strftime(local_observed_at, '%w') as integer) as weekday_index,
    extract(hour from local_observed_at)::integer as hour_of_day,
    count(*) as observation_count,
    count(*) filter (where is_disrupted) as disrupted_observation_count,
    round(
        100.0 * count(*) filter (where is_disrupted)
        / nullif(count(*), 0),
        2
    ) as observed_disruption_pct
from local_polls
group by service_date, line_id, weekday_index, hour_of_day
