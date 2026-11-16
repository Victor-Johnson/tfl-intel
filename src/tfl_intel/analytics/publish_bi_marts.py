"""Publish tested DuckDB marts to a read-only Postgres BI schema."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql

from tfl_intel.config import load_settings

BI_SCHEMA = "analytics"
BI_READER_ROLE = "metabase_reader"
BI_MARTS = (
    "current_line_status",
    "dim_line",
    "dim_status_severity",
    "disruption_events",
    "line_reliability_daily",
    "line_reliability_rolling_7d",
    "line_disruption_hourly",
    "line_status_summary",
    "network_disruption_hourly",
    "network_status_mix_daily",
    "pipeline_freshness",
)


def postgres_type(duckdb_type: str) -> str:
    """Map the finite set of mart column types to Postgres types."""

    normalized = duckdb_type.upper()
    if normalized.startswith("DECIMAL("):
        return normalized
    return {
        "BIGINT": "BIGINT",
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "DOUBLE": "DOUBLE PRECISION",
        "FLOAT": "REAL",
        "HUGEINT": "NUMERIC",
        "INTEGER": "INTEGER",
        "SMALLINT": "SMALLINT",
        "TIMESTAMP": "TIMESTAMP",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
        "TIMESTAMPTZ": "TIMESTAMPTZ",
        "TINYINT": "SMALLINT",
        "UBIGINT": "NUMERIC",
        "UINTEGER": "BIGINT",
        "USMALLINT": "INTEGER",
        "UTINYINT": "SMALLINT",
        "VARCHAR": "TEXT",
    }[normalized]


def _reader_password() -> str | None:
    password_file = os.getenv("METABASE_READER_PASSWORD_FILE")
    if not password_file:
        return None
    path = Path(password_file)
    if not path.is_file():
        msg = f"Metabase reader password is missing: {path}"
        raise RuntimeError(msg)
    password = path.read_text(encoding="utf-8").strip()
    if not password or password == "change-me-metabase-reader":
        msg = "Replace the example Metabase reader password"
        raise RuntimeError(msg)
    return password


def _ensure_reader(cursor: psycopg.Cursor[Any], password: str | None) -> None:
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)",
        (BI_READER_ROLE,),
    )
    result = cursor.fetchone()
    if result is None:
        raise RuntimeError("Unable to inspect Postgres roles")
    role_exists = bool(result[0])
    role = sql.Identifier(BI_READER_ROLE)
    if not role_exists and password is None:
        msg = "Metabase reader role is missing; run the production bootstrap first"
        raise RuntimeError(msg)
    if not role_exists:
        assert password is not None
        cursor.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                role, sql.Literal(password)
            )
        )
    elif password is not None:
        cursor.execute(
            sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                role, sql.Literal(password)
            )
        )
    cursor.execute(
        sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(role)
    )
    cursor.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '15s'").format(role))
    cursor.execute(sql.SQL("ALTER ROLE {} SET search_path = analytics").format(role))


def _create_table_statement(
    table_name: str, columns: list[tuple[str, str]]
) -> sql.Composed:
    definitions = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(postgres_type(data_type)))
        for name, data_type in columns
    )
    return sql.SQL("CREATE TABLE {}.{} ({})").format(
        sql.Identifier(BI_SCHEMA),
        sql.Identifier(f"{table_name}__next"),
        definitions,
    )


def publish_marts(duckdb_path: str) -> dict[str, int]:
    """Atomically replace the Postgres BI tables and return published row counts."""

    settings = load_settings()
    published: dict[str, int] = {}
    with (
        duckdb.connect(duckdb_path, read_only=True) as source,
        psycopg.connect(settings.postgres_conninfo()) as destination,
        destination.cursor() as cursor,
    ):
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(BI_SCHEMA))
        )
        _ensure_reader(cursor, _reader_password())
        role = sql.Identifier(BI_READER_ROLE)
        cursor.execute("SELECT current_database()")
        database_result = cursor.fetchone()
        if database_result is None:
            raise RuntimeError("Unable to identify the Postgres database")
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database_result[0]), role
            )
        )
        cursor.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(BI_SCHEMA), role
            )
        )
        for private_schema in ("raw", "staging", "ml"):
            cursor.execute(
                sql.SQL("REVOKE ALL ON SCHEMA {} FROM {}").format(
                    sql.Identifier(private_schema), role
                )
            )

        for table_name in BI_MARTS:
            relation = f"{BI_SCHEMA}.{table_name}"
            description = source.execute(
                f'DESCRIBE SELECT * FROM "{BI_SCHEMA}"."{table_name}"'
            ).fetchall()
            columns = [(row[0], row[1]) for row in description]
            next_table = sql.Identifier(f"{table_name}__next")
            target_table = sql.Identifier(table_name)
            cursor.execute(
                sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                    sql.Identifier(BI_SCHEMA), next_table
                )
            )
            cursor.execute(_create_table_statement(table_name, columns))

            placeholders = sql.SQL(", ").join(sql.Placeholder() for _column in columns)
            insert = sql.SQL("INSERT INTO {}.{} VALUES ({})").format(
                sql.Identifier(BI_SCHEMA), next_table, placeholders
            )
            result = source.execute(f'SELECT * FROM "{BI_SCHEMA}"."{table_name}"')
            row_count = 0
            while rows := result.fetchmany(1_000):
                cursor.executemany(insert, rows)
                row_count += len(rows)

            cursor.execute(
                sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                    sql.Identifier(BI_SCHEMA), target_table
                )
            )
            cursor.execute(
                sql.SQL("ALTER TABLE {}.{} RENAME TO {}").format(
                    sql.Identifier(BI_SCHEMA), next_table, target_table
                )
            )
            cursor.execute(
                sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                    sql.Identifier(BI_SCHEMA), target_table, role
                )
            )
            published[relation] = row_count

    return published


def main() -> None:
    """Publish the configured analytical file for Metabase."""

    duckdb_path = os.getenv("DUCKDB_PATH", "/data/tfl_intel.duckdb")
    published = publish_marts(duckdb_path)
    details = ", ".join(f"{table}={count}" for table, count in published.items())
    print(f"Published BI marts: {details}")


if __name__ == "__main__":
    main()
