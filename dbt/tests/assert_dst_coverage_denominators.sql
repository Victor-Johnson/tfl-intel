{% if env_var('TFL_DBT_CI_FIXTURE', 'false') == 'true' %}
with expected as (
    select date '2026-03-29' as service_date,
        276 as day_buckets, 2004 as week_buckets, 100.0 as uptime_pct
    union all
    select date '2026-10-25', 300, 2028, 0.0
),
actual as (
    select
        daily.service_date,
        daily.expected_full_day_observations as day_buckets,
        rolling.expected_full_week_observations as week_buckets,
        daily.observed_uptime_pct as uptime_pct,
        daily.total_observations,
        daily.full_day_coverage_pct
    from {{ ref('mart_line_reliability_daily') }} as daily
    join {{ ref('mart_line_reliability_rolling_7d') }} as rolling
        on rolling.line_id = daily.line_id
        and rolling.window_end_date = daily.service_date
    where daily.line_id = 'dst-test'
)
select expected.service_date
from expected
left join actual using (service_date)
where actual.service_date is null
   or actual.day_buckets <> expected.day_buckets
   or actual.week_buckets <> expected.week_buckets
   or actual.uptime_pct <> expected.uptime_pct
   or actual.total_observations <> 1
   or actual.full_day_coverage_pct >= 1
{% else %}
select service_date, line_id
from {{ ref('mart_line_reliability_daily') }}
where expected_full_day_observations <> cast(date_diff(
    'minute',
    cast(service_date as timestamp) at time zone 'Europe/London',
    cast(service_date + interval 1 day as timestamp)
        at time zone 'Europe/London'
) / 5 as integer)
{% endif %}
