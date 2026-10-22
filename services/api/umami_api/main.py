import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Umami Avocado", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    environment: str
    live_lab_orders_enabled: bool


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=os.getenv("APP_ENV", "development"), live_lab_orders_enabled=False)


@app.get("/api/readiness")
def readiness() -> dict[str, str]:
    # Structural readiness only; DB and S3 checks belong to UA-003/UA-015.
    return {"status": "foundation-only"}
