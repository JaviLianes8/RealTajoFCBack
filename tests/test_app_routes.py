"""HTTP route smoke tests for the FastAPI application."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_root_endpoint_returns_running_message() -> None:
    """The root endpoint should return the expected heartbeat payload."""

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "RUNNING REAL TAJO BACK"}
