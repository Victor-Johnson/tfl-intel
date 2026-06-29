"""Postgres loader skeleton for the V1 raw ingestion layer."""

from collections.abc import Sequence
from typing import Any

from tfl_intel.config import Settings
from tfl_intel.ingestion.models.line_status import LineStatusObservation


class PostgresLoader:
    """Placeholder loader for future raw schema writes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def start_pipeline_run(self, source_name: str) -> str:
        """Create a pipeline run record and return its run identifier."""

        raise NotImplementedError("Pipeline run tracking is not implemented yet")

    def finish_pipeline_run(self, ingestion_run_id: str, *, status: str) -> None:
        """Mark a pipeline run as complete or failed."""

        raise NotImplementedError("Pipeline run tracking is not implemented yet")

    def insert_line_status_observations(
        self,
        observations: Sequence[LineStatusObservation],
        *,
        ingestion_run_id: str,
    ) -> None:
        """Insert parsed line status observations into raw Postgres tables."""

        raise NotImplementedError("Line status inserts are not implemented yet")

    def record_invalid_records(
        self,
        invalid_records: Sequence[dict[str, Any]],
        *,
        ingestion_run_id: str,
    ) -> None:
        """Persist invalid source records for audit and replay."""

        raise NotImplementedError("Invalid record tracking is not implemented yet")
