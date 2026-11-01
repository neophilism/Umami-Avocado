import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from umami_api.contracts import HealthResponse, ReadinessResponse, ResultOrigin
from umami_api.main import app, create_app


def health():
    return {"schema_version": "1.0", "status": "ok", "environment": "development",
            "live_lab_orders_enabled": False}


@pytest.mark.parametrize("patch", [
    {"schema_version": "2.0"}, {"status": "ready"}, {"environment": 123},
    {"environment": ""}, {"environment": "x" * 65}, {"owner_secret": "never-echo"},
    *({"live_lab_orders_enabled": value} for value in (True, 0, 1, "false", None)),
])
def test_health_contract_rejects_coercion_future_versions_and_extra_fields(patch):
    with pytest.raises(ValidationError):
        HealthResponse.model_validate({**health(), **patch})


@pytest.mark.parametrize("field", list(health()))
def test_every_health_field_is_required(field):
    value = health()
    del value[field]
    with pytest.raises(ValidationError):
        HealthResponse.model_validate(value)


def test_provenance_labels_are_permanent_distinct_values_not_physical_permissions():
    assert [item.value for item in ResultOrigin] == ["SIMULATED", "PHYSICAL"]
    with pytest.raises(ValueError):
        ResultOrigin("simulated")
    with pytest.raises(ValidationError):
        HealthResponse.model_validate({**health(), "result_origin": "PHYSICAL"})


def test_models_are_frozen_and_readiness_cannot_claim_later_integrations():
    response = HealthResponse.model_validate(health())
    with pytest.raises(ValidationError):
        response.live_lab_orders_enabled = True
    value = {"schema_version": "1.0", "status": "foundation-only",
             "live_lab_orders_enabled": False, "database_connected": False,
             "artifact_store_connected": False}
    for field in ("database_connected", "artifact_store_connected"):
        for unsupported in (True, 0, "false"):
            with pytest.raises(ValidationError):
                ReadinessResponse.model_validate({**value, field: unsupported})


@pytest.mark.parametrize(("method", "path", "kwargs", "status", "code"), [
    ("GET", "/api/private-owner-fixture", {}, 404, "not_found"),
    ("GET", "/api/health?owner=private-owner-fixture", {}, 400, "invalid_request"),
    ("GET", "/api/health", {"content": "private-owner-fixture"}, 400, "invalid_request"),
    ("POST", "/api/health", {}, 405, "method_not_allowed"),
    ("GET", "/api/readiness/", {}, 404, "not_found"),
])
def test_stable_error_envelopes_do_not_echo_unexpected_inputs(method, path, kwargs, status, code):
    response = TestClient(app).request(method, path, **kwargs)
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"schema_version", "error"}
    assert body["schema_version"] == "1.0"
    assert body["error"]["code"] == code
    assert "private-owner-fixture" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    if status == 405:
        assert response.headers["allow"] == "GET"


def test_unexpected_dependency_failure_is_a_generic_500_not_false_success():
    application = create_app()

    @application.get("/api/failure")
    def fail():
        raise RuntimeError("private-owner-fixture")

    response = TestClient(application, raise_server_exceptions=False).get("/api/failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private-owner-fixture" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_live_schema_is_versioned_read_only_and_matches_export():
    schema = app.openapi()
    assert schema["x-contract-version"] == "1.0"
    assert set(schema["paths"]) == {"/api/health", "/api/readiness"}
    for item in schema["paths"].values():
        assert set(item) == {"get"}
        assert set(item["get"]["responses"]) == {"200", "400", "404", "405", "500"}
    assert TestClient(app).get("/api/openapi.json").json() == schema
    assert "PHYSICAL" in json.dumps(schema["components"]["schemas"]["ResultOrigin"])
    assert TestClient(app).post("/api/lab/orders").status_code == 404


def test_bad_environment_is_rejected_without_exposing_its_value(monkeypatch):
    monkeypatch.setenv("APP_ENV", "private-owner-fixture\n")
    with pytest.raises(ValueError, match="public deployment label") as error:
        create_app()
    assert "private-owner-fixture" not in str(error.value)
