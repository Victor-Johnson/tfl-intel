select
    line_name,
    event_started_at,
    event_ended_at,
    worst_status_description,
    latest_reason,
    observation_count,
    observed_disruption_minutes,
    case
        when is_resolved then 'observed recovery'
        else 'unresolved in sampled data'
    end as resolution_state
from analytics.disruption_events
where line_id = {{line_id}}
  and event_started_at >= now() - interval '90 days'
order by event_started_at desc
limit 30;
