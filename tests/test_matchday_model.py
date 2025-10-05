"""Tests for the matchday domain model."""
from __future__ import annotations

from app.domain.models.matchday import Matchday, MatchFixture


def test_fixtures_for_team_filters_home_and_away_matches() -> None:
    """Only fixtures containing the requested team should be returned."""

    matchday = Matchday(
        number=1,
        fixtures=[
            MatchFixture(home_team="REAL SPORT", away_team="REAL TAJO"),
            MatchFixture(home_team="Another Club", away_team="Different"),
            MatchFixture(home_team="Club", away_team="Club Real Tajo"),
        ],
    )

    fixtures = matchday.fixtures_for_team("REAL TAJO")

    assert len(fixtures) == 2
    assert fixtures[0].away_team == "REAL TAJO"
    assert fixtures[1].away_team == "Club Real Tajo"


def test_fixtures_for_team_includes_bye_information() -> None:
    """Bye rounds for Real Tajo should be included in the filtered fixtures."""

    matchday = Matchday(
        number=2,
        fixtures=[
            MatchFixture(home_team="Real Tajo", away_team=None, is_bye=True),
            MatchFixture(home_team="Opponent", away_team="Other"),
        ],
    )

    fixtures = matchday.fixtures_for_team("REAL TAJO")

    assert len(fixtures) == 1
    assert fixtures[0].is_bye


def test_to_dict_normalizes_combined_names_for_real_tajo() -> None:
    """Serializing should split concatenated Real Tajo fixtures into two teams."""

    matchday = Matchday(
        number=3,
        fixtures=[
            MatchFixture(
                home_team="REAL SPORT REAL TAJO",
                away_team="RACING ARANJUEZ ALBIRROJA",
            )
        ],
    )

    payload = matchday.to_dict(team_name="REAL TAJO")

    assert payload == {
        "matchdayNumber": 3,
        "fixtures": [
            {
                "homeTeam": "REAL SPORT",
                "awayTeam": "REAL TAJO",
                "homeScore": None,
                "awayScore": None,
                "isBye": False,
            }
        ],
    }


def test_to_dict_preserves_real_tajo_variants_without_splitting() -> None:
    """Team variants such as Real Tajo CF should remain untouched when serializing."""

    matchday = Matchday(
        number=4,
        fixtures=[
            MatchFixture(
                home_team="RACING ARANJUEZ",
                away_team="REAL TAJO C.F.",
            )
        ],
    )

    payload = matchday.to_dict(team_name="REAL TAJO")

    assert payload["fixtures"][0]["homeTeam"] == "RACING ARANJUEZ"
    assert payload["fixtures"][0]["awayTeam"] == "REAL TAJO"
