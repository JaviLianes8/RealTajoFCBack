"""HTTP route smoke tests for the FastAPI application."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain.models.matchday_results import MatchResult, MatchdayResults
from app.main import create_app


class _StubMatchdayRepository:
    """Stub repository returning preconfigured matchday results for testing."""

    def __init__(self, matchday: MatchdayResults | None = None) -> None:
        self._matchday = matchday

    def save(self, matchday: MatchdayResults) -> None:  # pragma: no cover - not used in test
        self._matchday = matchday

    def load(self, matchday_number: int) -> MatchdayResults | None:
        if self._matchday and self._matchday.matchday == matchday_number:
            return self._matchday
        return None

    def load_last(self) -> MatchdayResults | None:
        return self._matchday


def test_root_endpoint_returns_running_message() -> None:
    """The root endpoint should return the expected heartbeat payload."""

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "RUNNING REAL TAJO BACK"}


def test_get_last_matchday_returns_stored_data() -> None:
    """The endpoint should return the stored matchday when available."""

    matchday = MatchdayResults(
        competition="League",
        season="2025-2026",
        matchday=4,
        matches=[
            MatchResult(home_team="Team A", away_team="Team B", home_score=2, away_score=1)
        ],
    )
    client = TestClient(
        create_app(matchday_repo=_StubMatchdayRepository(matchday))
    )

    response = client.get("/api/v1/matchdays/last")

    assert response.status_code == 200
    assert response.json()["matchday"] == 4


def test_get_matchday_returns_404_when_missing() -> None:
    """Requesting a non-existent matchday should yield a 404 error."""

    client = TestClient(create_app(matchday_repo=_StubMatchdayRepository()))

    response = client.get("/api/v1/matchdays/7")

    assert response.status_code == 404
