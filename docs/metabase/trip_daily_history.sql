with bounds as (
    select (now() at time zone 'Europe/London')::date as local_today
),
days as (
    select day::date as service_date
    from bounds,
         generate_series(
             local_today - 90, local_today - 1, interval '1 day'
         ) as calendar(day)
)
select
    days.service_date,
    daily.observed_uptime_pct,
    coalesce(daily.full_day_coverage_pct, 0) as coverage_pct,
    coalesce(daily.total_observations, 0) as observed_samples,
    coalesce(daily.coverage_quality, 'insufficient') as coverage_quality
from days
left join analytics.line_reliability_daily as daily
    on daily.service_date = days.service_date
   and daily.line_id = {{line_id}}
order by days.service_date;
