with localized as (
    select
        observed_at at time zone 'Europe/London' as local_observed_at,
        coalesce(mode_name, 'unknown') as mode_name,
        is_disrupted
    from {{ ref('int_line_status_per_poll') }}
)
select
    cast(local_observed_at as date) as service_date,
    mode_name,
    cast(strftime(local_observed_at, '%w') as integer) as weekday_index,
    strftime(local_observed_at, '%a') as weekday_name,
    extract(hour from local_observed_at)::integer as hour_of_day,
    count(*) as observation_count,
    count(*) filter (where is_disrupted) as disrupted_observation_count,
    round(
        100.0 * count(*) filter (where is_disrupted)
        / nullif(count(*), 0),
        2
    ) as disruption_pct
from localized
group by service_date, mode_name, weekday_index, weekday_name, hour_of_day
