with latest as (
    select max(service_date) as latest_date
    from analytics.line_reliability_daily
)
select
    mode_name,
    count(distinct line_id) as line_count,
    round(
        100.0 * sum(good_service_observations)
        / nullif(sum(total_observations), 0),
        2
    ) as observed_uptime_pct,
    round(avg(full_day_coverage_pct)::numeric, 2) as average_coverage_pct,
    sum(disrupted_observations) as disrupted_observations,
    sum(disruption_event_count) as disruption_event_count,
    round(avg(mean_recovery_minutes)::numeric, 2) as mean_recovery_minutes
from analytics.line_reliability_daily, latest
where service_date >= latest_date - interval '29 days'
[[and mode_name = {{mode_name}}]]
group by mode_name
order by observed_uptime_pct, mode_name;
