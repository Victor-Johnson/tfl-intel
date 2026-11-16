"""Execute a DuckDB SQL script against a database file."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb


def main() -> None:
    if len(sys.argv) < 3:
        msg = "Usage: run_duckdb_sql.py <duckdb_path> <sql_path> [<sql_path> ...]"
        raise SystemExit(msg)

    duckdb_path = sys.argv[1]
    sql_paths = [Path(value) for value in sys.argv[2:]]

    with duckdb.connect(duckdb_path) as conn:
        for sql_path in sql_paths:
            sql = sql_path.read_text(encoding="utf-8")
            conn.execute(sql)


if __name__ == "__main__":
    main()
