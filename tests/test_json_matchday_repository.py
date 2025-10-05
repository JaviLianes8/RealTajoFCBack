"""Tests for the JSON matchday repository implementation."""
from __future__ import annotations

from pathlib import Path

from app.domain.models.matchday_results import MatchResult, MatchdayResults
from app.infrastructure.repositories.json_matchday_repository import (
    JsonMatchdayRepository,
)


def test_repository_persists_and_loads_matchday(tmp_path: Path) -> None:
    """The repository should persist matchdays and load them back correctly."""

    repository = JsonMatchdayRepository(tmp_path)
    matchday = MatchdayResults(
        competition="League",
        season="2025-2026",
        matchday=5,
        matches=[
            MatchResult(home_team="Team A", away_team="Team B", home_score=1, away_score=0)
        ],
    )

    repository.save(matchday)
    loaded = repository.load(5)

    assert loaded == matchday


def test_repository_returns_latest_matchday(tmp_path: Path) -> None:
    """``load_last`` should return the matchday with the highest number."""

    repository = JsonMatchdayRepository(tmp_path)
    first = MatchdayResults(
        competition="League",
        season="2025-2026",
        matchday=1,
        matches=[],
    )
    second = MatchdayResults(
        competition="League",
        season="2025-2026",
        matchday=3,
        matches=[
            MatchResult(home_team="Team C", away_team="Team D", home_score=2, away_score=2)
        ],
    )

    repository.save(first)
    repository.save(second)

    latest = repository.load_last()

    assert latest == second
