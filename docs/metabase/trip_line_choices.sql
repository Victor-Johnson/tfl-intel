select
    line_id,
    line_name,
    mode_name,
    status_description,
    observed_at
from analytics.current_line_status
order by mode_name, line_name;
