select
    service_date,
    mode_name,
    status_description,
    is_disrupted,
    count(*) as row_count
from {{ ref('network_status_mix_daily') }}
group by service_date, mode_name, status_description, is_disrupted
having count(*) > 1
