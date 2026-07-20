from fastapi.testclient import TestClient


def test_dashboard_is_served(client: TestClient) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "TfL Reliability Intelligence" in response.text
    assert "/api/v1/lines/reliability" in response.text
