import pytest

from tfl_intel.analytics.publish_bi_marts import postgres_type


@pytest.mark.parametrize(
    ("duckdb_type", "expected"),
    [
        ("VARCHAR", "TEXT"),
        ("BIGINT", "BIGINT"),
        ("DOUBLE", "DOUBLE PRECISION"),
        ("TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ"),
        ("DECIMAL(12,2)", "DECIMAL(12,2)"),
    ],
)
def test_postgres_type_maps_supported_mart_types(
    duckdb_type: str, expected: str
) -> None:
    assert postgres_type(duckdb_type) == expected


def test_postgres_type_rejects_unknown_type() -> None:
    with pytest.raises(KeyError):
        postgres_type("MAP(VARCHAR, VARCHAR)")
