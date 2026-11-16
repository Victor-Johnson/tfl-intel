from pathlib import Path

import duckdb
import pytest
from scripts.manage_duckdb_snapshot import prepare, promote


def _create_database(path: Path, version: str) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE TABLE version (value VARCHAR)")
        conn.execute("INSERT INTO version VALUES (?)", [version])


def test_promote_preserves_old_reader_then_serves_new_snapshot(tmp_path: Path) -> None:
    live = tmp_path / "live.duckdb"
    candidate = tmp_path / "live_building.duckdb"
    _create_database(live, "old")
    _create_database(candidate, "new")

    with duckdb.connect(str(live), read_only=True) as old_reader:
        promote(live, candidate)
        assert old_reader.execute("SELECT value FROM version").fetchone() == ("old",)

    with duckdb.connect(str(live), read_only=True) as new_reader:
        assert new_reader.execute("SELECT value FROM version").fetchone() == ("new",)

    assert not candidate.exists()


def test_failed_build_does_not_change_live_snapshot(tmp_path: Path) -> None:
    live = tmp_path / "live.duckdb"
    candidate = tmp_path / "live_building.duckdb"
    _create_database(live, "old")
    _create_database(candidate, "bad")

    prepare(live, candidate)
    with pytest.raises(FileNotFoundError):
        promote(live, candidate)
    with duckdb.connect(str(live), read_only=True) as reader:
        assert reader.execute("SELECT value FROM version").fetchone() == ("old",)


def test_candidate_must_share_live_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="share a directory"):
        prepare(tmp_path / "live.duckdb", tmp_path / "other" / "candidate.duckdb")
