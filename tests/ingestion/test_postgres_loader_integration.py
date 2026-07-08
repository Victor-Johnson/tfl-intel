"""Integration tests for the Postgres loader.

Requires the local database: docker compose up -d postgres
Run with: uv run pytest -m integration
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from psycopg import Connection

from tfl_intel.ingestion.loaders.postgres_loader import (
    get_connection,
    insert_line_status_observations,
    mark_pipeline_failed,
    start_pipeline_run,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def conn() -> Iterator[Connection]:
    try:
        connection = get_connection()
    except Exception:  # pragma: no cover - environment guard
        pytest.skip("Postgres is not reachable; run docker compose up -d postgres")

    yield connection
    # Loader functions never commit, so rolling back leaves no trace.
    connection.rollback()
    connection.close()


def _observation() -> dict[str, object]:
    return {
        "line_id": "victoria",
        "line_name": "Victoria",
        "status_severity": 10,
        "status_description": "Good Service",
    }


def test_inserting_the_same_batch_twice_inserts_zero_new_rows(
    conn: Connection,
) -> None:
    """Deterministic observation IDs + ON CONFLICT make re-runs no-ops."""

    run_id = f"test-{uuid4().hex}"
    observed_at = datetime.now(UTC)

    start_pipeline_run(conn, run_id, "test", "/test")

    first = insert_line_status_observations(
        conn,
        [_observation()],
        ingestion_run_id=run_id,
        observed_at=observed_at,
    )
    second = insert_line_status_observations(
        conn,
        [_observation()],
        ingestion_run_id=run_id,
        observed_at=observed_at,
    )

    assert first == 1
    assert second == 0


def test_failed_run_is_recorded_with_error_message(conn: Connection) -> None:
    run_id = f"test-{uuid4().hex}"

    start_pipeline_run(conn, run_id, "test", "/test")
    mark_pipeline_failed(conn, run_id, "boom")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, error_message
            FROM raw.pipeline_runs
            WHERE ingestion_run_id = %s;
            """,
            (run_id,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "failed"
    assert row[1] == "boom"
