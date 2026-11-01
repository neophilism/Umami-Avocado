import os
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from umami_api.contracts import (
    CONTRACT_VERSION,
    ERROR_RESPONSES,
    ERRORS,
    ErrorDetail,
    ErrorEnvelope,
    HealthResponse,
    ReadinessResponse,
    ResultOrigin,
)


def error_response(status: int, headers: dict[str, str] | None = None) -> JSONResponse:
    status = status if status in ERRORS else 500
    code, message = ERRORS[status]
    body = ErrorEnvelope(
        schema_version=CONTRACT_VERSION, error=ErrorDetail(code=code, message=message)
    )
    return JSONResponse(body.model_dump(), status_code=status, headers=headers)


def create_app() -> FastAPI:
    environment = os.getenv("APP_ENV", "development")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", environment):
        raise ValueError("APP_ENV must be a public deployment label.")
    application = FastAPI(
        title="Umami Avocado", version="0.1.0", docs_url=None, redoc_url=None,
        openapi_url="/api/openapi.json", redirect_slashes=False,
    )

    @application.middleware("http")
    async def contract_boundary(request: Request, call_next):
        # Foundation operations accept no body/query. Never parse or echo inputs.
        if request.url.path.startswith("/api/") and (
            request.scope.get("query_string")
            or request.headers.get("content-length", "0") != "0"
            or "transfer-encoding" in request.headers
        ):
            response = error_response(400)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        headers = {"Allow": exc.headers["Allow"]} if exc.headers and "Allow" in exc.headers else None
        return error_response(exc.status_code, headers)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError):
        return error_response(400)

    @application.exception_handler(Exception)
    async def unexpected_error(_request: Request, _exc: Exception):
        return error_response(500, {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @application.get(
        "/api/health", operation_id="get_health", response_model=HealthResponse,
        responses=ERROR_RESPONSES,
    )
    def health() -> HealthResponse:
        return HealthResponse(
            schema_version=CONTRACT_VERSION, status="ok", environment=environment,
            live_lab_orders_enabled=False,
        )

    @application.get(
        "/api/readiness", operation_id="get_readiness", response_model=ReadinessResponse,
        responses=ERROR_RESPONSES,
    )
    def readiness() -> ReadinessResponse:
        return ReadinessResponse(
            schema_version=CONTRACT_VERSION, status="foundation-only",
            live_lab_orders_enabled=False, database_connected=False, artifact_store_connected=False,
        )

    def canonical_openapi():
        if application.openapi_schema is None:
            schema = get_openapi(
                title=application.title, version=application.version, routes=application.routes
            )
            schema["x-contract-version"] = CONTRACT_VERSION
            schema["components"]["schemas"]["ResultOrigin"] = {
                "title": "ResultOrigin", "type": "string",
                "enum": [item.value for item in ResultOrigin],
                "description": "Provenance only. Neither value grants physical authorization.",
            }
            application.openapi_schema = schema
        return application.openapi_schema

    application.openapi = canonical_openapi
    return application


app = create_app()
