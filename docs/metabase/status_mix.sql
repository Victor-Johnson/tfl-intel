with latest as (
    select max(service_date) as latest_date
    from analytics.network_status_mix_daily
)
select
    mode_name,
    status_description,
    is_disrupted,
    sum(observation_count) as observation_count
from analytics.network_status_mix_daily, latest
where service_date >= latest_date - interval '29 days'
[[and mode_name = {{mode_name}}]]
group by mode_name, status_description, is_disrupted
order by mode_name, observation_count desc;
