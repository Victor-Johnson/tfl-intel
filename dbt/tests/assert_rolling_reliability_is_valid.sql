select *
from {{ ref('mart_line_reliability_rolling_7d') }}
where observed_uptime_pct_7d not between 0 and 100
   or coverage_pct_7d not between 0 and 100
