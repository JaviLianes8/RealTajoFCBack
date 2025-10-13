"""Tests for the JSON-backed matchday repository."""
from __future__ import annotations

from pathlib import Path

from app.domain.models.matchday import Matchday, MatchFixture
from app.infrastructure.repositories.json_matchday_repository import JsonMatchdayRepository


def test_repository_persists_and_loads_matchday(tmp_path: Path) -> None:
    """Saving a matchday should persist it as JSON and allow reloading."""

    repository = JsonMatchdayRepository(tmp_path)
    matchday = Matchday(
        number=3,
        fixtures=[
            MatchFixture(home_team="Team A", away_team="Team B", home_score=1, away_score=0),
            MatchFixture(home_team="Resting", away_team=None, is_bye=True),
        ],
    )

    repository.save(matchday)

    loaded = repository.get(3)
    assert loaded == matchday


def test_repository_returns_last_matchday(tmp_path: Path) -> None:
    """The repository should return the matchday with the highest number."""

    repository = JsonMatchdayRepository(tmp_path)
    repository.save(
        Matchday(
            number=2,
            fixtures=[MatchFixture(home_team="Home", away_team="Away")],
        )
    )
    repository.save(
        Matchday(
            number=5,
            fixtures=[MatchFixture(home_team="Later", away_team="Opponent", home_score=2, away_score=2)],
        )
    )

    latest = repository.get_last()
    assert latest is not None
    assert latest.number == 5


def test_repository_deletes_matchdays(tmp_path: Path) -> None:
    """The repository should delete specific and latest matchday files."""

    repository = JsonMatchdayRepository(tmp_path)
    first = Matchday(number=1, fixtures=[])
    second = Matchday(number=2, fixtures=[])
    repository.save(first)
    repository.save(second)

    removed_specific = repository.delete(1)
    assert removed_specific is True
    assert repository.get(1) is None

    removed_latest = repository.delete_last()
    assert removed_latest is True
    assert repository.get(2) is None

    missing_delete = repository.delete_last()
    assert missing_delete is False
