"""CLI entrypoint for the TfL Line/Status ingestion vertical slice."""

from tfl_intel.common.logging import configure_logging, get_logger
from tfl_intel.config import load_settings
from tfl_intel.ingestion.clients.tfl_client import TfLLineClient
from tfl_intel.ingestion.parsers.line_status_parser import parse_line_status_response


def main() -> None:
    """Fetch and parse TfL line status data without requiring Postgres."""

    settings = load_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__, source="tfl_line_status")

    with TfLLineClient(settings) as client:
        payload = client.get_line_status_by_mode("tube")

    observations = parse_line_status_response(payload)
    logger.info("line_status_ingested", observation_count=len(observations))
    if observations:
        logger.info(
            "first_line_status_observation",
            observation=observations[0].model_dump(mode="json"),
        )


if __name__ == "__main__":
    main()
