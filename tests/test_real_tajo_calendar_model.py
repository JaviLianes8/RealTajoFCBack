"""Unit tests for the Real Tajo calendar domain models."""
from __future__ import annotations

from datetime import date

from app.domain.models.real_tajo_calendar import RealTajoMatch


def test_real_tajo_match_from_dict_accepts_missing_date() -> None:
    """Matches without an assigned date should keep the value unset."""

    match = RealTajoMatch.from_dict(
        {
            "stage": "Liga",
            "matchday": 5,
            "date": None,
            "opponent": "RIVAL FC",
            "is_home": True,
            "time": "18:00",
            "field": "Campo Municipal",
        }
    )

    assert match.match_date is None
    assert match.to_dict()["date"] is None


def test_real_tajo_match_from_dict_parses_valid_date() -> None:
    """Valid ISO dates must still be parsed into ``date`` instances."""

    match = RealTajoMatch.from_dict(
        {
            "stage": "Liga",
            "matchday": 6,
            "date": "2025-10-18",
            "opponent": "RIVAL FC",
            "is_home": False,
            "time": None,
            "field": None,
        }
    )

    assert match.match_date == date(2025, 10, 18)
    assert match.to_dict()["date"] == "2025-10-18"
