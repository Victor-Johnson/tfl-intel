select line_id, observation_bucket
from {{ ref('int_line_status_per_poll') }}
group by line_id, observation_bucket
having count(*) > 1
