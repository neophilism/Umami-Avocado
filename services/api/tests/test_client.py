import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from umami_api.generated_client import (
    ApiClient,
    ApiClientError,
    ProtocolError,
    Response,
    TransportError,
    validate_response,
)
from umami_api.main import create_app

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = json.loads((ROOT / "contracts/client-examples.json").read_text())


def response(body, status=200, content_type="application/json"):
    return Response(status, content_type, json.dumps(body).encode())


def test_generated_python_client_consumes_actual_fastapi_routes(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    calls = []
    with TestClient(create_app()) as server:
        def transport(path, timeout):
            calls.append((path, timeout))
            result = server.get(path)
            return Response(result.status_code, result.headers["content-type"], result.content)
        client = ApiClient("https://synthetic.example", transport=transport)
        assert client.get_health() == EXAMPLES["health"]
        assert client.get_readiness() == EXAMPLES["readiness"]
    assert calls == [("/api/health", 5), ("/api/readiness", 5)]


@pytest.mark.parametrize("body", EXAMPLES["invalidHealth"])
def test_shared_invalid_response_corpus_is_rejected(body):
    assert validate_response("HealthResponse", body) is False
    client = ApiClient("https://synthetic.example", transport=lambda _p, _t: response(body))
    with pytest.raises(ProtocolError):
        client.get_health()


def test_malformed_encoding_content_types_large_bodies_and_unknown_statuses_fail_closed():
    for item in [Response(200, "application/json", b"not-json"),
                 Response(200, "application/json", b"\xff"),
                 Response(200, "text/html", b"<html>private-fixture</html>"),
                 Response(200, "application/json", b" " * 65537),
                 response(EXAMPLES["health"], 302), response(EXAMPLES["health"], 503)]:
        client = ApiClient("https://synthetic.example", transport=lambda _p, _t, r=item: r)
        with pytest.raises(ProtocolError) as error:
            client.get_health()
        assert "private-fixture" not in str(error.value)
    assert validate_response("UnknownFutureType", {}) is False


def test_typed_error_and_mismatched_status_code_are_not_success():
    envelope = {"schema_version": "1.0", "error": {"code": "internal_error", "message": "private-fixture"}}
    client = ApiClient("https://synthetic.example", transport=lambda _p, _t: response(envelope, 500))
    with pytest.raises(ApiClientError) as error:
        client.get_health()
    assert error.value.status == 500
    assert error.value.detail == envelope
    assert "private-fixture" not in str(error.value)
    with pytest.raises(ProtocolError):
        ApiClient("https://synthetic.example", transport=lambda _p, _t: response(envelope, 404)).get_health()


@pytest.mark.parametrize("failure", [OSError("private-fixture"), TimeoutError("private-fixture")])
def test_dependency_failures_do_not_retry_or_expose_transport_details(failure):
    calls = []
    def transport(path, _timeout):
        calls.append(path)
        raise failure
    with pytest.raises(TransportError) as error:
        ApiClient("https://synthetic.example", transport=transport).get_health()
    assert calls == ["/api/health"]
    assert "private-fixture" not in str(error.value)


@pytest.mark.parametrize("origin", ["", "http://remote.example", "https://user:private@example.test",
                                   "https://example.test/path", "https://example.test?x=1",
                                   "https://example.test#fragment", "https://example.test/\n",
                                   "https://example.test:invalid"])
def test_bad_origin_is_rejected_before_any_request(origin):
    with pytest.raises(ValueError):
        ApiClient(origin, transport=lambda _p, _t: pytest.fail("unexpected request"))


@pytest.mark.parametrize("timeout", [0, -1, 61, True, float("nan"), float("inf"), "5"])
def test_timeout_must_be_bounded_and_typed(timeout):
    with pytest.raises(ValueError):
        ApiClient("https://synthetic.example", timeout_seconds=timeout)


def test_default_transport_uses_local_http_and_never_follows_redirects():
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/must-not-follow")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
        def log_message(self, _format, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ProtocolError):
            ApiClient(f"http://127.0.0.1:{server.server_port}").get_health()
        assert calls == ["/api/health"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_default_transport_dependency_refusal_is_not_reported_ready():
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        port = holder.getsockname()[1]
        with pytest.raises(TransportError):
            ApiClient(f"http://127.0.0.1:{port}", timeout_seconds=0.1).get_readiness()
