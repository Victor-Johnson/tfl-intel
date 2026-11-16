select
    line_name,
    mode_name,
    observed_uptime_pct_7d,
    coverage_pct_7d,
    total_observations_7d
from analytics.line_reliability_rolling_7d
where window_end_date = (
    select max(window_end_date)
    from analytics.line_reliability_rolling_7d
)
  and window_end_date >= (now() at time zone 'Europe/London')::date - 1
  and coverage_pct_7d >= 90
order by observed_uptime_pct_7d, line_name;
