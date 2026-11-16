select
    service_date,
    mode_name,
    weekday_index,
    hour_of_day,
    count(*) as row_count
from {{ ref('network_disruption_hourly') }}
group by service_date, mode_name, weekday_index, hour_of_day
having count(*) > 1
