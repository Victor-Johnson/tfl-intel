from tfl_intel.common.ids import (
    make_observation_id,
    make_status_fingerprint,
    stable_hash,
)


def test_same_input_gives_same_stable_hash() -> None:
    assert stable_hash("central|good") == stable_hash("central|good")


def test_different_reason_gives_different_status_fingerprint() -> None:
    first = make_status_fingerprint(
        "central",
        "Minor Delays",
        "Synthetic reason one.",
        "2026-06-29T08:00:00Z",
        "2026-06-29T09:00:00Z",
    )
    second = make_status_fingerprint(
        "central",
        "Minor Delays",
        "Synthetic reason two.",
        "2026-06-29T08:00:00Z",
        "2026-06-29T09:00:00Z",
    )

    assert first != second


def test_different_ingestion_run_id_gives_different_observation_id() -> None:
    fingerprint = make_status_fingerprint("central", "Good Service", None, None, None)

    assert make_observation_id("central", fingerprint, "run-1") != make_observation_id(
        "central", fingerprint, "run-2"
    )
