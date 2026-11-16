"""Integration tests for the Postgres loader.

Requires the local database: docker compose up -d postgres
Run with: uv run pytest -m integration
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import respx
from httpx import Response
from psycopg import Connection
from pytest import MonkeyPatch

from tfl_intel.config import Settings
from tfl_intel.ingestion.jobs import ingest_line_status
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
        if os.getenv("REQUIRE_INTEGRATION_DB") == "1":
            raise
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


def test_new_run_retains_another_observation(conn: Connection) -> None:
    observed_at = datetime.now(UTC)
    first_run = f"test-{uuid4().hex}"
    second_run = f"test-{uuid4().hex}"
    for run_id in (first_run, second_run):
        start_pipeline_run(conn, run_id, "test", "/test")

    first = insert_line_status_observations(
        conn, [_observation()], ingestion_run_id=first_run, observed_at=observed_at
    )
    second = insert_line_status_observations(
        conn, [_observation()], ingestion_run_id=second_run, observed_at=observed_at
    )

    assert (first, second) == (1, 1)


def test_failed_write_rolls_back_observations_but_keeps_failed_run(
    conn: Connection, monkeypatch: MonkeyPatch
) -> None:
    conn.execute("SELECT 1")  # Keep the test's outer transaction for rollback.
    run_ids: list[str] = []

    class ConnectionProxy:
        def transaction(self):
            return conn.transaction()

        def cursor(self):
            return conn.cursor()

        def close(self) -> None:
            pass

    def record_run(**kwargs: object) -> None:
        run_ids.append(str(kwargs["ingestion_run_id"]))
        start_pipeline_run(**kwargs)

    def insert_then_fail(**kwargs: object) -> int:
        insert_line_status_observations(**kwargs)
        raise RuntimeError("synthetic failure after insert")

    monkeypatch.setattr(ingest_line_status, "get_connection", ConnectionProxy)
    monkeypatch.setattr(
        ingest_line_status,
        "load_settings",
        lambda: Settings(tfl_api_base_url="https://api.example.test/Line"),
    )
    monkeypatch.setattr(ingest_line_status, "start_pipeline_run", record_run)
    monkeypatch.setattr(
        ingest_line_status, "insert_line_status_observations", insert_then_fail
    )
    payload = [
        {
            "id": "central",
            "name": "Central",
            "lineStatuses": [
                {"statusSeverity": 10, "statusSeverityDescription": "Good Service"}
            ],
        }
    ]
    with respx.mock(base_url="https://api.example.test") as router:
        router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(200, json=payload)
        )
        with pytest.raises(RuntimeError, match="synthetic failure after insert"):
            ingest_line_status.run("tube")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM raw.pipeline_runs WHERE ingestion_run_id = %s",
            (run_ids[0],),
        )
        assert cur.fetchone() == ("failed",)
        cur.execute(
            "SELECT COUNT(*) FROM raw.tfl_line_status_observations "
            "WHERE ingestion_run_id = %s",
            (run_ids[0],),
        )
        assert cur.fetchone() == (0,)


def test_retention_prunes_only_expired_raw_history(conn: Connection) -> None:
    old_run = f"test-{uuid4().hex}"
    recent_run = f"test-{uuid4().hex}"
    old_time = datetime(2025, 1, 1, tzinfo=UTC)
    recent_time = datetime.now(UTC)
    for run_id in (old_run, recent_run):
        start_pipeline_run(conn, run_id, "test", "/test")
    conn.execute(
        "UPDATE raw.pipeline_runs SET started_at = %s WHERE ingestion_run_id = %s",
        (old_time, old_run),
    )
    for run_id, observed_at in ((old_run, old_time), (recent_run, recent_time)):
        assert (
            insert_line_status_observations(
                conn, [_observation()], ingestion_run_id=run_id, observed_at=observed_at
            )
            == 1
        )

    sql_path = Path(__file__).resolve().parents[2] / "sql/maintenance/prune_raw_90d.sql"
    conn.execute(sql_path.read_text(encoding="utf-8"))
    assert conn.execute(
        "SELECT COUNT(*) FROM raw.tfl_line_status_observations "
        "WHERE ingestion_run_id = %s",
        (old_run,),
    ).fetchone() == (0,)
    assert conn.execute(
        "SELECT COUNT(*) FROM raw.tfl_line_status_observations "
        "WHERE ingestion_run_id = %s",
        (recent_run,),
    ).fetchone() == (1,)
    assert conn.execute(
        "SELECT COUNT(*) FROM raw.pipeline_runs WHERE ingestion_run_id = %s",
        (old_run,),
    ).fetchone() == (0,)
    assert conn.execute(
        "SELECT COUNT(*) FROM raw.pipeline_runs WHERE ingestion_run_id = %s",
        (recent_run,),
    ).fetchone() == (1,)
