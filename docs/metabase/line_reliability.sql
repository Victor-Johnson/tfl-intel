select
    mode_name,
    line_name,
    observed_uptime_pct_7d,
    coverage_pct_7d,
    coverage_quality_7d,
    estimated_disruption_minutes_7d,
    disruption_event_count_7d
from analytics.line_reliability_rolling_7d
where window_end_date = (
    select max(window_end_date)
    from analytics.line_reliability_rolling_7d
)
[[and mode_name = {{mode_name}}]]
order by observed_uptime_pct_7d, line_name;
