with latest as (
    select max(service_date) as latest_date
    from analytics.network_disruption_hourly
)
select
    mode_name,
    weekday_index,
    weekday_name,
    hour_of_day,
    sum(disrupted_observation_count) as disrupted_observations,
    sum(observation_count) as total_observations,
    round(
        100.0 * sum(disrupted_observation_count)
        / nullif(sum(observation_count), 0),
        2
    ) as disruption_pct
from analytics.network_disruption_hourly, latest
where service_date >= latest_date - interval '89 days'
[[and mode_name = {{mode_name}}]]
group by mode_name, weekday_index, weekday_name, hour_of_day
order by mode_name, weekday_index, hour_of_day;
