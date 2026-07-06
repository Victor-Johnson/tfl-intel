"""CLI entrypoint for ingesting TfL line metadata into Postgres."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tfl_intel.common.logging import configure_logging, get_logger
from tfl_intel.config import load_settings
from tfl_intel.ingestion.clients.tfl_client import TfLLineClient
from tfl_intel.ingestion.loaders.postgres_loader import (
    get_connection,
    insert_lines,
    mark_pipeline_failed,
    mark_pipeline_success,
    start_pipeline_run,
)


def main() -> None:
    """Fetch TfL tube line metadata and upsert it into Postgres."""

    run()


def run(mode: str = "tube") -> int:
    """Run line metadata ingestion and return upserted row count."""

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__, source="tfl_lines")

    ingestion_run_id = f"lines-{mode}-{datetime.now(UTC).isoformat()}-{uuid4().hex[:8]}"
    source_name = "tfl_line_api"
    source_endpoint = f"/Mode/{mode}"

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
                payload = client.get_lines_by_mode(mode)

            upserted_count = insert_lines(conn, payload)
            mark_pipeline_success(
                conn=conn,
                ingestion_run_id=ingestion_run_id,
                records_received=len(payload),
                records_inserted=upserted_count,
                records_rejected=0,
            )

            logger.info(
                "lines_loaded_to_postgres",
                ingestion_run_id=ingestion_run_id,
                records_received=len(payload),
                records_inserted=upserted_count,
                mode=mode,
            )
            return upserted_count

    except Exception as exc:
        with conn.transaction():
            mark_pipeline_failed(conn, ingestion_run_id, str(exc))

        logger.exception(
            "lines_ingestion_failed",
            ingestion_run_id=ingestion_run_id,
            error=str(exc),
            mode=mode,
        )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
