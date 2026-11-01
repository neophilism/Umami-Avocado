import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from umami_api.main import app

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = runpy.run_path(str(ROOT / "scripts/generate-api-clients.py"))
generate = GENERATOR["generate_files"]
check_or_write = GENERATOR["check_or_write"]


def test_checked_in_openapi_and_both_clients_are_reproducible_and_current():
    outputs = generate(app.openapi())
    assert set(outputs) == {
        "contracts/openapi.json", "contracts/manifest.json",
        "apps/web/src/generated/api.ts", "services/api/umami_api/generated_client.py",
    }
    assert check_or_write(ROOT, outputs, check=True) == []
    assert outputs == generate(copy.deepcopy(app.openapi()))
    manifest = json.loads(outputs["contracts/manifest.json"])
    for path, digest in manifest["sha256"].items():
        assert hashlib.sha256(outputs[path].encode()).hexdigest() == digest


def test_drift_check_fails_without_rewriting_stale_or_missing_artifacts(tmp_path):
    outputs = generate(app.openapi())
    assert len(check_or_write(tmp_path, outputs, check=True)) == 4
    check_or_write(tmp_path, outputs, check=False)
    path = tmp_path / "apps/web/src/generated/api.ts"
    path.write_text("stale client")
    assert check_or_write(tmp_path, outputs, check=True) == ["apps/web/src/generated/api.ts"]
    assert path.read_text() == "stale client"


@pytest.mark.parametrize("mutation", [
    lambda d: d.update({"x-contract-version": "2.0"}),
    lambda d: d.update({"security": [{"unreviewed": []}]}),
    lambda d: d["components"]["schemas"]["HealthResponse"].update({"additionalProperties": True}),
    lambda d: d["components"]["schemas"]["HealthResponse"].update({"required": []}),
    lambda d: d["components"]["schemas"]["HealthResponse"]["properties"]["environment"].update({"format": "unknown"}),
    lambda d: d["components"]["schemas"]["HealthResponse"]["properties"]["environment"].update({"type": "integer"}),
    lambda d: d["components"]["schemas"]["HealthResponse"]["properties"]["environment"].update({"$ref": "https://example.test/schema"}),
    lambda d: d["components"]["schemas"]["HealthResponse"]["properties"]["environment"].update({"pattern": "(?=unsupported)"}),
    lambda d: d["paths"]["/api/health"].update({"post": {}}),
    lambda d: d["paths"]["/api/health"]["get"].update({"requestBody": {"required": True}}),
    lambda d: d["paths"]["/api/health"]["get"].update({"operationId": "class"}),
    lambda d: d["paths"]["/api/health"]["get"]["responses"].pop("500"),
])
def test_unsupported_contract_features_fail_generation_instead_of_weakening_types(mutation):
    document = copy.deepcopy(app.openapi())
    mutation(document)
    with pytest.raises(ValueError):
        generate(document)
