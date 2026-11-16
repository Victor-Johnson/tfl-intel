select *
from {{ ref('network_disruption_hourly') }}
where observation_count < 0
   or disrupted_observation_count < 0
   or disrupted_observation_count > observation_count
   or disruption_pct not between 0 and 100
   or weekday_index not between 0 and 6
   or hour_of_day not between 0 and 23
