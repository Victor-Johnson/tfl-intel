from fastapi.testclient import TestClient


def test_current_status_returns_expected_schema(client: TestClient) -> None:
    response = client.get("/api/v1/lines/current-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["line_id"] == "central"
    assert payload[0]["line_name"] == "Central"
    assert payload[0]["status_description"] == "Minor Delays"
    assert payload[0]["status_severity"] == 9
    assert payload[0]["reason"] == "Synthetic signal failure."
    assert payload[0]["ingestion_run_id"] == "run-2"


def test_line_history_respects_limit(client: TestClient) -> None:
    response = client.get("/api/v1/lines/central/history?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["observation_id"] == "obs-2"


def test_line_history_rejects_invalid_limit(client: TestClient) -> None:
    response = client.get("/api/v1/lines/central/history?limit=501")

    assert response.status_code == 422
