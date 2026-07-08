"""CLI entrypoint for ingesting TfL Line Status data into Postgres."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tfl_intel.common.logging import configure_logging, get_logger
from tfl_intel.config import load_settings
from tfl_intel.ingestion.clients.tfl_client import TfLLineClient
from tfl_intel.ingestion.loaders.postgres_loader import (
    get_connection,
    insert_line_status_observations,
    mark_pipeline_failed,
    mark_pipeline_success,
    start_pipeline_run,
)
from tfl_intel.ingestion.parsers.line_status_parser import parse_line_status_response


def main() -> None:
    """Fetch TfL line status data, parse it, and insert observations into Postgres."""

    run()


def run() -> int:
    """Run the line status ingestion job and return inserted observation count."""

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__, source="tfl_line_status")

    ingestion_run_id = f"line-status-{datetime.now(UTC).isoformat()}-{uuid4().hex[:8]}"
    source_name = "tfl_line_api"
    source_endpoint = "/Mode/tube/Status"
    observed_at = datetime.now(UTC)

    conn = get_connection()

    try:
        with conn.transaction():
            start_pipeline_run(
                conn=conn,
                ingestion_run_id=ingestion_run_id,
                source_name=source_name,
                source_endpoint=source_endpoint,
            )

        with conn.transaction():
            with TfLLineClient(settings) as client:
                payload = client.get_line_status_by_mode("tube")

            observations = parse_line_status_response(payload)

            inserted_count = insert_line_status_observations(
                conn=conn,
                observations=observations,
                ingestion_run_id=ingestion_run_id,
                observed_at=observed_at,
                source_endpoint=source_endpoint,
            )

            mark_pipeline_success(
                conn=conn,
                ingestion_run_id=ingestion_run_id,
                records_received=len(observations),
                records_inserted=inserted_count,
                records_rejected=0,
            )

            logger.info(
                "line_status_loaded_to_postgres",
                ingestion_run_id=ingestion_run_id,
                records_received=len(observations),
                records_inserted=inserted_count,
            )

            return inserted_count

    except Exception as exc:
        with conn.transaction():
            mark_pipeline_failed(
                conn=conn,
                ingestion_run_id=ingestion_run_id,
                error_message=str(exc),
            )

        logger.exception(
            "line_status_ingestion_failed",
            ingestion_run_id=ingestion_run_id,
            error=str(exc),
        )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
