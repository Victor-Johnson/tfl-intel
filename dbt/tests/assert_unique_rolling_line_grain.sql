select window_end_date, line_id
from {{ ref('mart_line_reliability_rolling_7d') }}
group by window_end_date, line_id
having count(*) > 1
