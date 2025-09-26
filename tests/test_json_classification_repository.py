from __future__ import annotations

from pathlib import Path

from datetime import date

from app.domain.models.classification import (
    ClassificationLastMatch,
    ClassificationLastMatchTeam,
    ClassificationRow,
    ClassificationTable,
)
from app.infrastructure.repositories.json_classification_repository import (
    JsonClassificationRepository,
)


def build_table() -> ClassificationTable:
    row = ClassificationRow(
        position=1,
        team="ALBIRROJA",
        stats={
            "points": 9,
            "played": 3,
            "wins": 3,
            "draws": 0,
            "losses": 0,
            "goals_for": 7,
            "goals_against": 2,
            "last_points": 9,
            "sanction_points": 0,
        },
        raw="1ALBIRROJA 93030720",
    )
    last_match = ClassificationLastMatch(
        matchday=1,
        date=date(2025, 10, 11),
        home_team=ClassificationLastMatchTeam(name="REAL TAJO", score=0),
        away_team=ClassificationLastMatchTeam(name="RACING ARANJUEZ", score=0),
    )
    return ClassificationTable(headers=["Equipos", "Puntos"], rows=[row], last_match=last_match)


def test_repository_persists_and_loads_classification_table(tmp_path: Path) -> None:
    repository = JsonClassificationRepository(tmp_path / "classification.json")
    table = build_table()

    repository.save(table)
    loaded = repository.load()

    assert loaded == table


def test_repository_returns_none_when_file_is_missing(tmp_path: Path) -> None:
    repository = JsonClassificationRepository(tmp_path / "missing.json")

    assert repository.load() is None
