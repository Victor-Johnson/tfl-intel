select
    line_id,
    line_name,
    status_description,
    status_severity,
    count(*) as observation_count,
    min(observed_at) as first_observed_at,
    max(observed_at) as last_observed_at
from {{ ref('int_line_status_per_poll') }}
group by line_id, line_name, status_description, status_severity

