select *
from {{ ref('fct_disruption_events') }}
where event_duration_minutes < 0
