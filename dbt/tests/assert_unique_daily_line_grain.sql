select service_date, line_id
from {{ ref('mart_line_reliability_daily') }}
group by service_date, line_id
having count(*) > 1
