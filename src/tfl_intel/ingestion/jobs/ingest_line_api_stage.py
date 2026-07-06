"""Run the complete TfL Line API raw ingestion stage."""

from __future__ import annotations

from tfl_intel.common.logging import configure_logging, get_logger
from tfl_intel.config import load_settings
from tfl_intel.ingestion.jobs.ingest_line_status import run as run_line_status
from tfl_intel.ingestion.jobs.ingest_lines_by_mode import run as run_lines_by_mode
from tfl_intel.ingestion.jobs.ingest_severity_codes import run as run_severity_codes


def main() -> None:
    """Run severity, line metadata, and line status ingestion jobs."""

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__, source="tfl_line_api_stage")

    severity_count = run_severity_codes()
    lines_count = run_lines_by_mode("tube")
    status_count = run_line_status()

    logger.info(
        "line_api_stage_loaded_to_postgres",
        severity_records=severity_count,
        line_records=lines_count,
        status_records=status_count,
    )


if __name__ == "__main__":
    main()
