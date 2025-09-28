"""Tests for the JSON top scorers repository implementation."""
from __future__ import annotations

from pathlib import Path

from app.domain.models.top_scorers import TopScorerEntry, TopScorersTable
from app.infrastructure.repositories.json_top_scorers_repository import (
    JsonTopScorersRepository,
)


def test_json_top_scorers_repository_roundtrip(tmp_path: Path) -> None:
    """Saving and loading a top scorers table should preserve its data."""

    repository = JsonTopScorersRepository(tmp_path / "top_scorers.json")
    table = TopScorersTable(
        title="Liga Example",
        competition="Liga Example",
        category="Categoria",
        season="2025-2026",
        scorers=[
            TopScorerEntry(
                player="PLAYER, ONE",
                team="TEAM",
                group="Grupo",
                matches_played=3,
                goals_total=5,
                goals_details="5",
                penalty_goals=None,
                goals_per_match=1.67,
                raw_lines=["PLAYER, ONE TEAM Grupo 3 5 1,6700"],
            )
        ],
    )

    repository.save(table)
    loaded = repository.load()

    assert loaded == table

