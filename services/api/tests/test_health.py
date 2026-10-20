from fastapi.testclient import TestClient

from umami_api.main import app


def test_health_never_claims_live_lab_orders():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["live_lab_orders_enabled"] is False


def test_readiness_is_explicitly_foundation_only():
    assert TestClient(app).get("/api/readiness").json()["status"] == "foundation-only"
