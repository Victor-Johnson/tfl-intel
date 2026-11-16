select *
from {{ ref('mart_line_reliability_daily') }}
where observed_uptime_pct not between 0 and 100
   or full_day_coverage_pct not between 0 and 100
   or good_service_observations + disrupted_observations
      <> total_observations
