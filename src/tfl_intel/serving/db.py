"""DuckDB helpers for the read-only serving API."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import duckdb

from tfl_intel.serving.config import load_settings

REQUIRED_ANALYTICS_TABLES = (
    "analytics.current_line_status",
    "analytics.line_status_summary",
    "analytics.pipeline_freshness",
)


def duckdb_path_exists(path: str | None = None) -> bool:
    """Return whether the configured DuckDB file exists."""

    db_path = Path(path or load_settings().duckdb_path)
    return db_path.exists()


def fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    """Run a read-only DuckDB query and return rows as dictionaries."""

    with duckdb.connect(load_settings().duckdb_path, read_only=True) as conn:
        result = conn.execute(query, params)
        columns = [column[0] for column in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def fetch_one(query: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
    """Run a read-only DuckDB query and return the first row if present."""

    rows = fetch_all(query, params)
    if not rows:
        return None
    return rows[0]


def check_required_tables() -> tuple[bool, list[str]]:
    """Check whether required analytics tables exist in the DuckDB file."""

    if not duckdb_path_exists():
        return False, list(REQUIRED_ANALYTICS_TABLES)

    rows = fetch_all(
        """
        SELECT table_schema || '.' || table_name AS table_name
        FROM information_schema.tables
        WHERE table_schema = 'analytics'
        """
    )
    existing = {row["table_name"] for row in rows}
    missing = [
        table_name
        for table_name in REQUIRED_ANALYTICS_TABLES
        if table_name not in existing
    ]
    return not missing, missing
