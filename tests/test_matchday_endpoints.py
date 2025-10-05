"""Integration tests for matchday endpoints."""
from __future__ import annotations

from typing import Dict

from fastapi.testclient import TestClient

from app.application.process_matchday import MatchdayParser
from app.domain.models.matchday import Matchday, MatchFixture
from app.domain.repositories.matchday_repository import MatchdayRepository
from app.main import create_app


class _StubMatchdayParser(MatchdayParser):
    """Stub parser returning a predefined matchday."""

    def __init__(self, matchday: Matchday) -> None:
        self._matchday = matchday
        self.received_bytes: bytes | None = None

    def parse(self, document_bytes: bytes) -> Matchday:  # noqa: D401 - protocol compliance
        """Return the stored matchday while remembering the input bytes."""

        self.received_bytes = document_bytes
        return self._matchday


class _InMemoryMatchdayRepository(MatchdayRepository):
    """In-memory repository used to test the HTTP layer."""

    def __init__(self) -> None:
        self._data: Dict[int, Matchday] = {}

    def save(self, matchday: Matchday) -> None:  # noqa: D401 - protocol compliance
        """Store the given matchday in memory."""

        self._data[matchday.number] = matchday

    def get(self, number: int) -> Matchday | None:  # noqa: D401 - protocol compliance
        """Return the stored matchday for ``number`` if present."""

        return self._data.get(number)

    def get_last(self) -> Matchday | None:  # noqa: D401 - protocol compliance
        """Return the matchday with the highest key in memory."""

        if not self._data:
            return None
        return self._data[max(self._data)]


def test_upload_and_retrieve_matchday_endpoints() -> None:
    """Uploading a matchday should persist it and allow retrieval."""

    matchday = Matchday(
        number=7,
        fixtures=[
            MatchFixture(
                home_team="Team A",
                away_team="REAL TAJO",
                home_score=2,
                away_score=1,
            ),
            MatchFixture(home_team="Rest", away_team=None, is_bye=True),
        ],
    )
    parser = _StubMatchdayParser(matchday)
    repository = _InMemoryMatchdayRepository()
    app = create_app(matchday_parser=parser, matchday_repo=repository)
    client = TestClient(app)

    response = client.put(
        "/api/v1/matchdays",
        files={"file": ("matchday.pdf", b"pdf-bytes", "application/pdf")},
    )

    assert response.status_code == 200
    expected_payload = matchday.to_dict(team_name="REAL TAJO")
    assert response.json() == expected_payload
    assert response.headers["Location"] == "/api/v1/matchdays/7"
    assert repository.get(7) == matchday
    assert parser.received_bytes == b"pdf-bytes"

    retrieved = client.get("/api/v1/matchdays/7")
    assert retrieved.status_code == 200
    assert retrieved.json() == expected_payload

    latest = client.get("/api/v1/matchdays/last")
    assert latest.status_code == 200
    assert latest.json() == expected_payload


def test_matchday_endpoints_return_not_found_when_empty() -> None:
    """Retrieving absent matchdays should result in ``404`` responses."""

    app = create_app(matchday_parser=_StubMatchdayParser(Matchday(1, [])), matchday_repo=_InMemoryMatchdayRepository())
    client = TestClient(app)

    response_number = client.get("/api/v1/matchdays/99")
    assert response_number.status_code == 404

    response_last = client.get("/api/v1/matchdays/last")
    assert response_last.status_code == 404
