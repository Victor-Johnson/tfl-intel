from tfl_intel.common.ids import (
    make_observation_id,
    make_status_fingerprint,
    stable_hash,
)


def test_stable_hash_is_deterministic() -> None:
    assert stable_hash("central|good") == stable_hash("central|good")
    assert stable_hash("central|good") != stable_hash("central|minor delays")


def test_status_fingerprint_is_deterministic() -> None:
    first = make_status_fingerprint(
        "central",
        "Good Service",
        None,
        None,
        None,
    )
    second = make_status_fingerprint(
        "central",
        "Good Service",
        None,
        None,
        None,
    )

    assert first == second
    assert len(first) == 64


def test_observation_id_includes_ingestion_run() -> None:
    fingerprint = make_status_fingerprint("central", "Good Service", None, None, None)

    assert make_observation_id("central", fingerprint, "run-1") != make_observation_id(
        "central", fingerprint, "run-2"
    )
