"""Prepare and atomically promote a validated DuckDB build file."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _check_paths(live: Path, candidate: Path) -> None:
    if live.resolve() == candidate.resolve():
        raise ValueError("Candidate must differ from the live DuckDB file")
    if live.parent.resolve() != candidate.parent.resolve():
        raise ValueError("Candidate and live DuckDB files must share a directory")


def prepare(live: Path, candidate: Path) -> None:
    """Discard only a stale candidate left by a previous failed build."""

    _check_paths(live, candidate)
    candidate.unlink(missing_ok=True)
    Path(f"{candidate}.wal").unlink(missing_ok=True)


def promote(live: Path, candidate: Path) -> None:
    """Replace the live database after dbt and invariant checks have passed."""

    _check_paths(live, candidate)
    if not candidate.is_file():
        raise FileNotFoundError(f"DuckDB candidate is missing: {candidate}")
    if Path(f"{candidate}.wal").exists():
        raise RuntimeError("DuckDB candidate still has a WAL; close all writers")
    os.replace(candidate, live)


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[1] not in {"prepare", "promote"}:
        raise SystemExit(
            "Usage: manage_duckdb_snapshot.py prepare|promote LIVE CANDIDATE"
        )
    action, live, candidate = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if action == "prepare":
        prepare(live, candidate)
    else:
        promote(live, candidate)


if __name__ == "__main__":
    main()
