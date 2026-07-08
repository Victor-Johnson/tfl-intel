from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "tfl-intel-serving"}


def test_ready_returns_structured_response(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["duckdb_file_exists"] is True
    assert payload["checks"]["analytics_tables_exist"] is True
    assert payload["missing_tables"] == []
