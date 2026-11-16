with status_observations as (
    select
        cast(observed_at at time zone 'Europe/London' as date) as service_date,
        coalesce(mode_name, 'unknown') as mode_name,
        status_description,
        is_disrupted
    from {{ ref('int_line_status_per_poll') }}
)
select
    service_date,
    mode_name,
    status_description,
    is_disrupted,
    count(*) as observation_count
from status_observations
group by service_date, mode_name, status_description, is_disrupted
