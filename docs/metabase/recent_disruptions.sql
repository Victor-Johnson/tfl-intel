select
    event_started_at,
    mode_name,
    line_name,
    worst_status_description,
    event_duration_minutes,
    observed_disruption_minutes,
    is_resolved,
    latest_reason
from analytics.disruption_events
where true
[[and mode_name = {{mode_name}}]]
order by event_started_at desc
limit 250;
