from fastapi.testclient import TestClient


def test_pipeline_freshness_returns_expected_schema(client: TestClient) -> None:
    response = client.get("/api/v1/pipeline/freshness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ingestion_run_id"] == "run-2"
    assert payload["status"] == "success"
    assert payload["records_inserted"] == 11
    assert payload["minutes_since_latest_success"] == 4


def test_pipeline_latest_run_returns_expected_schema(client: TestClient) -> None:
    response = client.get("/api/v1/pipeline/latest-run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ingestion_run_id"] == "run-2"
    assert payload["records_received"] == 11
