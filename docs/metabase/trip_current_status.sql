select
    line_name,
    mode_name,
    status_description,
    reason,
    observed_at,
    round(extract(epoch from now() - observed_at) / 60.0, 1)
        as observation_age_minutes,
    case
        when now() - observed_at > interval '15 minutes' then 'stale'
        else 'current'
    end as freshness
from analytics.current_line_status
where line_id = {{line_id}};
