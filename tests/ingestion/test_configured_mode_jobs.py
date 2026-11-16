from pytest import MonkeyPatch

from tfl_intel.ingestion.jobs import ingest_line_status, ingest_lines_by_mode


class _ConfiguredModes:
    def configured_tfl_modes(self) -> tuple[str, ...]:
        return ("tube", "elizabeth-line", "dlr", "overground", "tram")


def test_status_job_runs_every_configured_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(ingest_line_status, "load_settings", lambda: _ConfiguredModes())
    calls: list[str] = []
    monkeypatch.setattr(ingest_line_status, "run", calls.append)
    ingest_line_status.main()

    assert calls == ["tube", "elizabeth-line", "dlr", "overground", "tram"]


def test_reference_job_runs_every_configured_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        ingest_lines_by_mode, "load_settings", lambda: _ConfiguredModes()
    )
    calls: list[str] = []
    monkeypatch.setattr(ingest_lines_by_mode, "run", calls.append)

    ingest_lines_by_mode.main()

    assert calls == ["tube", "elizabeth-line", "dlr", "overground", "tram"]
