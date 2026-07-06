from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from tfl_intel.common.ids import make_observation_id, make_status_fingerprint
from tfl_intel.config import get_settings


def get_connection() -> Connection:
    """Open a psycopg connection using configured DATABASE_URL."""

    settings = get_settings()
    return psycopg.connect(settings.database_url)


def start_pipeline_run(
    conn: Connection,
    ingestion_run_id: str,
    source_name: str,
    source_endpoint: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.pipeline_runs (
                ingestion_run_id,
                source_name,
                source_endpoint,
                status,
                started_at
            )
            VALUES (%s, %s, %s, 'started', NOW())
            ON CONFLICT (ingestion_run_id) DO NOTHING;
            """,
            (ingestion_run_id, source_name, source_endpoint),
        )


def mark_pipeline_success(
    conn: Connection,
    ingestion_run_id: str,
    records_received: int,
    records_inserted: int,
    records_rejected: int = 0,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE raw.pipeline_runs
            SET
                status = 'success',
                finished_at = NOW(),
                records_received = %s,
                records_inserted = %s,
                records_rejected = %s,
                error_message = NULL
            WHERE ingestion_run_id = %s;
            """,
            (
                records_received,
                records_inserted,
                records_rejected,
                ingestion_run_id,
            ),
        )


def mark_pipeline_failed(
    conn: Connection,
    ingestion_run_id: str,
    error_message: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE raw.pipeline_runs
            SET
                status = 'failed',
                finished_at = NOW(),
                error_message = %s
            WHERE ingestion_run_id = %s;
            """,
            (error_message, ingestion_run_id),
        )


def _as_dict(observation: Any) -> dict[str, Any]:
    if hasattr(observation, "model_dump"):
        return observation.model_dump()
    if isinstance(observation, dict):
        return observation
    raise TypeError(f"Unsupported observation type: {type(observation)}")


def insert_line_status_observations(
    conn: Connection,
    observations: list[Any],
    ingestion_run_id: str,
    observed_at: datetime,
) -> int:
    inserted = 0

    with conn.cursor() as cur:
        for observation in observations:
            row = _as_dict(observation)

            status_fingerprint = make_status_fingerprint(
                line_id=row["line_id"],
                status_description=row["status_description"],
                reason=row.get("reason"),
                validity_start=row.get("validity_start"),
                validity_end=row.get("validity_end"),
            )

            observation_id = make_observation_id(
                line_id=row["line_id"],
                status_fingerprint=status_fingerprint,
                ingestion_run_id=ingestion_run_id,
            )

            cur.execute(
                """
                INSERT INTO raw.tfl_line_status_observations (
                    observation_id,
                    status_fingerprint,
                    ingestion_run_id,
                    line_id,
                    line_name,
                    mode_name,
                    status_id,
                    status_severity,
                    status_description,
                    reason,
                    status_created_at,
                    status_modified_at,
                    validity_start,
                    validity_end,
                    validity_is_now,
                    observed_at,
                    source_endpoint,
                    raw_payload
                )
                VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (observation_id) DO NOTHING;
                """,
                (
                    observation_id,
                    status_fingerprint,
                    ingestion_run_id,
                    row["line_id"],
                    row["line_name"],
                    row.get("mode_name"),
                    row.get("status_id"),
                    row["status_severity"],
                    row["status_description"],
                    row.get("reason"),
                    row.get("status_created"),
                    row.get("status_modified"),
                    row.get("validity_start"),
                    row.get("validity_end"),
                    row.get("validity_is_now"),
                    observed_at,
                    "/Mode/tube/Status",
                    Jsonb(row.get("raw_payload", row)),
                ),
            )

            if cur.rowcount == 1:
                inserted += 1

    return inserted


def insert_status_severity_codes(
    conn: Connection,
    severity_codes: list[dict[str, Any]],
) -> int:
    """Insert or update TfL status severity code metadata."""

    upserted = 0
    ingested_at = datetime.now(UTC)

    with conn.cursor() as cur:
        for item in severity_codes:
            severity_level = item.get("severityLevel")
            description = item.get("description")
            if severity_level is None or not description:
                msg = "Severity code is missing severityLevel or description"
                raise ValueError(msg)

            mode_name = item.get("modeName")
            cur.execute(
                """
                UPDATE raw.tfl_status_severity_codes
                SET
                    description = %s,
                    source_endpoint = %s,
                    ingested_at = %s,
                    raw_payload = %s
                WHERE
                    severity_level = %s
                    AND mode_name IS NOT DISTINCT FROM %s;
                """,
                (
                    str(description),
                    "/Meta/Severity",
                    ingested_at,
                    Jsonb(item),
                    int(severity_level),
                    mode_name,
                ),
            )

            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO raw.tfl_status_severity_codes (
                        severity_level,
                        mode_name,
                        description,
                        source_endpoint,
                        ingested_at,
                        raw_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (
                        int(severity_level),
                        mode_name,
                        str(description),
                        "/Meta/Severity",
                        ingested_at,
                        Jsonb(item),
                    ),
                )

            upserted += 1

    return upserted


def insert_lines(
    conn: Connection,
    lines: list[dict[str, Any]],
) -> int:
    """Insert or update TfL line metadata."""

    upserted = 0
    ingested_at = datetime.now(UTC)

    with conn.cursor() as cur:
        for item in lines:
            line_id = item.get("id")
            line_name = item.get("name")
            if not line_id or not line_name:
                msg = "TfL line item is missing id or name"
                raise ValueError(msg)

            cur.execute(
                """
                INSERT INTO raw.tfl_lines (
                    line_id,
                    line_name,
                    mode_name,
                    created_source_at,
                    modified_source_at,
                    source_endpoint,
                    ingested_at,
                    raw_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (line_id) DO UPDATE
                SET
                    line_name = EXCLUDED.line_name,
                    mode_name = EXCLUDED.mode_name,
                    created_source_at = EXCLUDED.created_source_at,
                    modified_source_at = EXCLUDED.modified_source_at,
                    source_endpoint = EXCLUDED.source_endpoint,
                    ingested_at = EXCLUDED.ingested_at,
                    raw_payload = EXCLUDED.raw_payload;
                """,
                (
                    str(line_id),
                    str(line_name),
                    item.get("modeName"),
                    item.get("created"),
                    item.get("modified"),
                    "/Mode/tube",
                    ingested_at,
                    Jsonb(item),
                ),
            )
            upserted += 1

    return upserted
