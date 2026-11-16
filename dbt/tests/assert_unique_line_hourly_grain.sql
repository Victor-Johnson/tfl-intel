select line_id, service_date, hour_of_day
from {{ ref('line_disruption_hourly') }}
group by line_id, service_date, hour_of_day
having count(*) > 1
