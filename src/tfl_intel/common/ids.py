"""Deterministic identifier helpers for raw observations."""

from collections.abc import Iterable
from hashlib import sha256


def stable_hash(value: str) -> str:
    """Return a deterministic SHA-256 hex digest for a string value."""

    return sha256(value.encode("utf-8")).hexdigest()


def _join_parts(parts: Iterable[str | None]) -> str:
    return "|".join("" if part is None else part.strip() for part in parts)


def make_observation_id(
    line_id: str, status_fingerprint: str, ingestion_run_id: str
) -> str:
    """Create a stable observation identifier for one pipeline run."""

    return stable_hash(_join_parts([line_id, status_fingerprint, ingestion_run_id]))


def make_status_fingerprint(
    line_id: str,
    status_description: str,
    reason: str | None,
    validity_start: str | None,
    validity_end: str | None,
) -> str:
    """Create a stable fingerprint for the passenger-visible status state."""

    return stable_hash(
        _join_parts([line_id, status_description, reason, validity_start, validity_end])
    )
