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

    def delete(self, number: int) -> bool:  # noqa: D401 - protocol compliance
        """Remove the matchday identified by ``number`` when present."""

        return self._data.pop(number, None) is not None

    def delete_last(self) -> bool:  # noqa: D401 - protocol compliance
        """Remove the matchday with the highest key when present."""

        if not self._data:
            return False
        highest = max(self._data)
        del self._data[highest]
        return True


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


def test_save_latest_matchday_endpoint() -> None:
    """Posting a matchday payload should persist and expose it as latest."""

    repository = _InMemoryMatchdayRepository()
    app = create_app(
        matchday_parser=_StubMatchdayParser(Matchday(1, [])),
        matchday_repo=repository,
    )
    client = TestClient(app)

    payload = {
        "matchdayNumber": 3,
        "fixtures": [
            {
                "homeTeam": "LA VESPA",
                "awayTeam": "REAL TAJO",
                "homeScore": 0,
                "awayScore": 1,
                "isBye": False,
                "date": "2025-10-25",
                "time": "17:00",
            }
        ],
    }

    response = client.post("/api/v1/matchdays/last", json=payload)

    assert response.status_code == 201
    expected = Matchday.from_dict(payload).to_dict(team_name="REAL TAJO")
    assert response.json() == expected
    assert response.headers["Location"] == "/api/v1/matchdays/3"
    assert repository.get(3) == Matchday.from_dict(payload)

    latest = client.get("/api/v1/matchdays/last")
    assert latest.status_code == 200
    assert latest.json() == expected


def test_save_latest_cup_matchday_endpoint() -> None:
    """Posting a cup matchday payload should persist and expose it as latest."""

    cup_repository = _InMemoryMatchdayRepository()
    app = create_app(
        matchday_parser=_StubMatchdayParser(Matchday(1, [])),
        matchday_repo=_InMemoryMatchdayRepository(),
        matchday_cup_repo=cup_repository,
    )
    client = TestClient(app)

    payload = {
        "matchdayNumber": 1,
        "fixtures": [
            {
                "homeTeam": "REAL TAJO",
                "awayTeam": "RIVAL COPA FC",
                "homeScore": 2,
                "awayScore": 0,
                "isBye": False,
            }
        ],
    }

    response = client.post("/api/v1/matchdays/last/copa", json=payload)

    assert response.status_code == 201
    expected = Matchday.from_dict(payload).to_dict(team_name="REAL TAJO")
    assert response.json() == expected
    assert response.headers["Location"] == "/api/v1/matchdays/last/copa"
    assert cup_repository.get(1) == Matchday.from_dict(payload)

    latest = client.get("/api/v1/matchdays/last/copa")
    assert latest.status_code == 200
    assert latest.json() == expected


def test_matchday_endpoints_return_not_found_when_empty() -> None:
    """Retrieving absent matchdays should result in ``404`` responses."""

    app = create_app(matchday_parser=_StubMatchdayParser(Matchday(1, [])), matchday_repo=_InMemoryMatchdayRepository())
    client = TestClient(app)

    response_number = client.get("/api/v1/matchdays/99")
    assert response_number.status_code == 404

    response_last = client.get("/api/v1/matchdays/last")
    assert response_last.status_code == 404

    delete_number = client.delete("/api/v1/matchdays/99")
    assert delete_number.status_code == 404

    delete_last = client.delete("/api/v1/matchdays/last")
    assert delete_last.status_code == 404

    last_cup = client.get("/api/v1/matchdays/last/copa")
    assert last_cup.status_code == 404

    delete_last_cup = client.delete("/api/v1/matchdays/last/copa")
    assert delete_last_cup.status_code == 404


def test_delete_matchday_endpoints() -> None:
    """Deleting matchdays should remove the stored resources."""

    repository = _InMemoryMatchdayRepository()
    first = Matchday(number=1, fixtures=[])
    second = Matchday(number=2, fixtures=[])
    repository.save(first)
    repository.save(second)
    app = create_app(matchday_parser=_StubMatchdayParser(second), matchday_repo=repository)
    client = TestClient(app)

    delete_specific = client.delete("/api/v1/matchdays/1")
    assert delete_specific.status_code == 204
    assert repository.get(1) is None

    delete_latest = client.delete("/api/v1/matchdays/last")
    assert delete_latest.status_code == 204
    assert repository.get(2) is None


def test_modify_latest_matchday_endpoint() -> None:
    """Modifying the latest matchday should replace its stored data."""

    repository = _InMemoryMatchdayRepository()
    existing = Matchday(
        number=2,
        fixtures=[
            MatchFixture(
                home_team="REAL TAJO",
                away_team="Team A",
                home_score=1,
                away_score=0,
            )
        ],
    )
    repository.save(existing)
    app = create_app(matchday_parser=_StubMatchdayParser(existing), matchday_repo=repository)
    client = TestClient(app)

    payload = {
        "matchdayNumber": 2,
        "fixtures": [
            {
                "homeTeam": "REAL TAJO",
                "awayTeam": "Team B",
                "homeScore": 3,
                "awayScore": 1,
                "isBye": False,
                "date": "2025-10-19",
                "time": "13:40",
            }
        ],
    }

    response = client.put("/api/v1/matchdays/last/modify", json=payload)

    assert response.status_code == 200
    assert response.json() == Matchday.from_dict(payload).to_dict(team_name="REAL TAJO")
    stored = repository.get(2)
    assert stored == Matchday.from_dict(payload)


def test_modify_latest_cup_matchday_endpoint() -> None:
    """Modifying the latest cup matchday should replace its stored data."""

    cup_repository = _InMemoryMatchdayRepository()
    existing = Matchday(number=4, fixtures=[])
    cup_repository.save(existing)
    app = create_app(
        matchday_parser=_StubMatchdayParser(existing),
        matchday_repo=_InMemoryMatchdayRepository(),
        matchday_cup_repo=cup_repository,
    )
    client = TestClient(app)

    payload = {
        "matchdayNumber": 4,
        "fixtures": [
            {
                "homeTeam": "RIVAL COPA FC",
                "awayTeam": "REAL TAJO",
                "homeScore": 1,
                "awayScore": 3,
                "isBye": False,
            }
        ],
    }

    response = client.put("/api/v1/matchdays/last/modify/copa", json=payload)

    assert response.status_code == 200
    assert response.json() == Matchday.from_dict(payload).to_dict(team_name="REAL TAJO")
    assert cup_repository.get(4) == Matchday.from_dict(payload)


def test_modify_latest_matchday_returns_conflict_on_mismatch() -> None:
    """Providing a different matchday number should raise a conflict error."""

    repository = _InMemoryMatchdayRepository()
    repository.save(Matchday(number=3, fixtures=[]))
    app = create_app(matchday_parser=_StubMatchdayParser(Matchday(3, [])), matchday_repo=repository)
    client = TestClient(app)

    payload = {
        "matchdayNumber": 4,
        "fixtures": [],
    }

    response = client.put("/api/v1/matchdays/last/modify", json=payload)

    assert response.status_code == 409


def test_modify_latest_matchday_returns_not_found_when_absent() -> None:
    """Attempting to modify without stored matchdays should return not found."""

    app = create_app(matchday_parser=_StubMatchdayParser(Matchday(1, [])), matchday_repo=_InMemoryMatchdayRepository())
    client = TestClient(app)

    payload = {
        "matchdayNumber": 1,
        "fixtures": [],
    }

    response = client.put("/api/v1/matchdays/last/modify", json=payload)

    assert response.status_code == 404


def test_modify_latest_matchday_returns_bad_request_on_invalid_payload() -> None:
    """Invalid payloads should result in a ``400`` response."""

    repository = _InMemoryMatchdayRepository()
    repository.save(Matchday(number=1, fixtures=[]))
    app = create_app(matchday_parser=_StubMatchdayParser(Matchday(1, [])), matchday_repo=repository)
    client = TestClient(app)

    payload = {
        "matchdayNumber": "not-a-number",
        "fixtures": [],
    }

    response = client.put("/api/v1/matchdays/last/modify", json=payload)

    assert response.status_code == 400


def test_save_latest_matchday_returns_bad_request_on_invalid_payload() -> None:
    """Invalid payloads posted to /matchdays/last should return bad request."""

    repository = _InMemoryMatchdayRepository()
    app = create_app(
        matchday_parser=_StubMatchdayParser(Matchday(1, [])),
        matchday_repo=repository,
    )
    client = TestClient(app)

    payload = {
        "matchdayNumber": "not-a-number",
        "fixtures": [],
    }

    response = client.post("/api/v1/matchdays/last", json=payload)

    assert response.status_code == 400
