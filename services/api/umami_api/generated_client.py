"""Generated from canonical OpenAPI. No credentials, retries or lab dispatch.

Contract SHA-256: 74c19a24be681ff8c1230eb058e07fa5f9d52365247ffc5fe18f22bec3b32302
"""
from __future__ import annotations

import http.client
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypedDict, cast
from urllib.parse import urlsplit


class ErrorDetail(TypedDict):
    code: Literal['invalid_request', 'not_found', 'method_not_allowed', 'internal_error']
    message: str

class ErrorEnvelope(TypedDict):
    error: ErrorDetail
    schema_version: Literal['1.0']

class HealthResponse(TypedDict):
    environment: str
    live_lab_orders_enabled: Literal[False]
    schema_version: Literal['1.0']
    status: Literal['ok']

class ReadinessResponse(TypedDict):
    artifact_store_connected: Literal[False]
    database_connected: Literal[False]
    live_lab_orders_enabled: Literal[False]
    schema_version: Literal['1.0']
    status: Literal['foundation-only']

ResultOrigin = Literal['SIMULATED', 'PHYSICAL']

CONTRACT_DIGEST = "74c19a24be681ff8c1230eb058e07fa5f9d52365247ffc5fe18f22bec3b32302"
SCHEMAS = json.loads('{"ErrorDetail":{"additionalProperties":false,"properties":{"code":{"enum":["invalid_request","not_found","method_not_allowed","internal_error"],"title":"Code","type":"string"},"message":{"maxLength":200,"minLength":1,"title":"Message","type":"string"}},"required":["code","message"],"title":"ErrorDetail","type":"object"},"ErrorEnvelope":{"additionalProperties":false,"properties":{"error":{"$ref":"#/components/schemas/ErrorDetail"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"}},"required":["schema_version","error"],"title":"ErrorEnvelope","type":"object"},"HealthResponse":{"additionalProperties":false,"properties":{"environment":{"maxLength":64,"minLength":1,"pattern":"^[a-z][a-z0-9_-]*$","title":"Environment","type":"string"},"live_lab_orders_enabled":{"const":false,"title":"Live Lab Orders Enabled","type":"boolean"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"status":{"const":"ok","title":"Status","type":"string"}},"required":["schema_version","live_lab_orders_enabled","status","environment"],"title":"HealthResponse","type":"object"},"ReadinessResponse":{"additionalProperties":false,"properties":{"artifact_store_connected":{"const":false,"title":"Artifact Store Connected","type":"boolean"},"database_connected":{"const":false,"title":"Database Connected","type":"boolean"},"live_lab_orders_enabled":{"const":false,"title":"Live Lab Orders Enabled","type":"boolean"},"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"status":{"const":"foundation-only","title":"Status","type":"string"}},"required":["schema_version","live_lab_orders_enabled","status","database_connected","artifact_store_connected"],"title":"ReadinessResponse","type":"object"},"ResultOrigin":{"description":"Provenance only. Neither value grants physical authorization.","enum":["SIMULATED","PHYSICAL"],"title":"ResultOrigin","type":"string"}}')
OPERATIONS = json.loads('{"get_health":{"errors":{"400":{"code":"invalid_request","schema":"ErrorEnvelope"},"404":{"code":"not_found","schema":"ErrorEnvelope"},"405":{"code":"method_not_allowed","schema":"ErrorEnvelope"},"500":{"code":"internal_error","schema":"ErrorEnvelope"}},"path":"/api/health","response":"HealthResponse"},"get_readiness":{"errors":{"400":{"code":"invalid_request","schema":"ErrorEnvelope"},"404":{"code":"not_found","schema":"ErrorEnvelope"},"405":{"code":"method_not_allowed","schema":"ErrorEnvelope"},"500":{"code":"internal_error","schema":"ErrorEnvelope"}},"path":"/api/readiness","response":"ReadinessResponse"}}')
MAX_RESPONSE_BYTES = 65536


class ProtocolError(Exception):
    def __init__(self):
        super().__init__("The service response does not match the API contract.")


class TransportError(Exception):
    def __init__(self):
        super().__init__("The API request could not be completed.")


class ApiClientError(Exception):
    def __init__(self, status: int, detail: ErrorEnvelope):
        self.status = status
        self.detail = detail
        super().__init__("The API returned " + detail["error"]["code"] + ".")


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str
    body: bytes


def _valid(value: object, schema: dict, depth: int = 0) -> bool:
    if depth > 32:
        return False
    if "$ref" in schema:
        target = SCHEMAS.get(schema["$ref"].removeprefix("#/components/schemas/"))
        return target is not None and _valid(value, target, depth + 1)
    if schema.get("type") == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        return all(key not in properties or _valid(item, properties[key], depth + 1)
                   for key, item in value.items())
    if schema.get("type") == "string":
        if not isinstance(value, str):
            return False
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", MAX_RESPONSE_BYTES):
            return False
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            return False
    elif schema.get("type") == "boolean":
        if type(value) is not bool:
            return False
    else:
        return False
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        return False
    return "enum" not in schema or value in schema["enum"]


def validate_response(name: str, value: object) -> bool:
    return name in SCHEMAS and _valid(value, SCHEMAS[name])


class ApiClient:
    def __init__(self, base_url: str, *, transport: Callable[[str, float], Response] | None = None,
                 timeout_seconds: float = 5):
        if not isinstance(base_url, str) or re.search(r"[\\\x00-\x20\x7f]", base_url):
            raise ValueError("Configure an API origin.")
        url = urlsplit(base_url)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or url.path not in ("", "/") or
                not (url.scheme == "https" or (local and url.scheme == "http"))):
            raise ValueError("Configure an HTTPS or loopback API origin.")
        # Validate the port now; never turn a malformed configuration into a request.
        try:
            _ = url.port
        except ValueError:
            raise ValueError("Configure a valid API origin port.") from None
        if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
                or not 0 < timeout_seconds <= 60):
            raise ValueError("Use a timeout above zero and at most sixty seconds.")
        self._url = url
        self._transport = transport or self._send
        self._timeout = timeout_seconds

    def _send(self, path: str, timeout: float) -> Response:
        cls = http.client.HTTPSConnection if self._url.scheme == "https" else http.client.HTTPConnection
        connection = cls(self._url.hostname, self._url.port, timeout=timeout)
        try:
            connection.request("GET", path, headers={"Accept": "application/json"})
            response = connection.getresponse()
            # http.client does not follow redirects or retry uncertain requests.
            return Response(response.status, response.getheader("Content-Type", ""),
                            response.read(MAX_RESPONSE_BYTES + 1))
        finally:
            connection.close()

    def _request(self, operation_id: str) -> object:
        operation = OPERATIONS[operation_id]
        try:
            response = self._transport(operation["path"], self._timeout)
        except (OSError, http.client.HTTPException):
            raise TransportError() from None
        if (not isinstance(response, Response) or type(response.status) is not int
                or not isinstance(response.content_type, str)
                or not isinstance(response.body, bytes) or len(response.body) > MAX_RESPONSE_BYTES
                or response.content_type.split(";", 1)[0].strip().lower() != "application/json"):
            raise ProtocolError()
        try:
            body = json.loads(response.body.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise ProtocolError() from None
        if response.status == 200:
            if not validate_response(operation["response"], body):
                raise ProtocolError()
            return body
        error = operation["errors"].get(str(response.status))
        if not error or not validate_response(error["schema"], body) or body["error"]["code"] != error["code"]:
            raise ProtocolError()
        raise ApiClientError(response.status, cast(ErrorEnvelope, body))

    def get_health(self) -> HealthResponse:
        return cast(HealthResponse, self._request('get_health'))

    def get_readiness(self) -> ReadinessResponse:
        return cast(ReadinessResponse, self._request('get_readiness'))
