select
    ingestion_run_id,
    status as latest_snapshot_run_status,
    latest_success_finished_at,
    round(
        extract(epoch from now() - latest_success_finished_at) / 60.0,
        1
    ) as minutes_since_latest_snapshot_run,
    case
        when latest_success_finished_at is null then 'no data'
        when now() - latest_success_finished_at > interval '15 minutes'
            then 'stale'
        else 'current'
    end as snapshot_freshness
from analytics.pipeline_freshness;
