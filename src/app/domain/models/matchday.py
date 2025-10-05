"""Domain models describing matchday fixtures and results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


def _normalize_team_name(name: str | None) -> str:
    """Return a normalized version of ``name`` for case-insensitive comparisons."""

    if name is None:
        return ""
    return " ".join(name.strip().casefold().split())


@dataclass(frozen=True)
class MatchFixture:
    """Represent a single fixture, optionally including the final score."""

    home_team: str
    away_team: str | None
    home_score: int | None = None
    away_score: int | None = None
    is_bye: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the fixture."""

        return {
            "homeTeam": self.home_team,
            "awayTeam": self.away_team,
            "homeScore": self.home_score,
            "awayScore": self.away_score,
            "isBye": self.is_bye,
        }

    def involves_team(self, team_name: str) -> bool:
        """Return ``True`` when the fixture features the provided ``team_name``."""

        normalized_target = _normalize_team_name(team_name)
        if not normalized_target:
            return False

        home_name = _normalize_team_name(self.home_team)
        away_name = _normalize_team_name(self.away_team)

        if self.is_bye:
            return normalized_target in home_name

        return normalized_target in home_name or (
            bool(away_name) and normalized_target in away_name
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MatchFixture:
        """Create a fixture instance from its serialized representation."""

        home_team = str(data.get("homeTeam", "")).strip()
        away_team_raw = data.get("awayTeam")
        away_team = str(away_team_raw).strip() if away_team_raw is not None else None

        def _to_optional_int(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        home_score = _to_optional_int(data.get("homeScore"))
        away_score = _to_optional_int(data.get("awayScore"))
        is_bye = bool(data.get("isBye", False))

        return cls(
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            is_bye=is_bye,
        )


@dataclass(frozen=True)
class Matchday:
    """Aggregate representing all fixtures associated with a matchday."""

    number: int
    fixtures: list[MatchFixture] = field(default_factory=list)

    def fixtures_for_team(self, team_name: str) -> list[MatchFixture]:
        """Return the fixtures involving ``team_name`` within the matchday."""

        normalized_target = _normalize_team_name(team_name)
        if not normalized_target:
            return []

        return [
            fixture for fixture in self.fixtures if fixture.involves_team(team_name)
        ]

    def to_dict(self, team_name: str | None = None) -> dict[str, Any]:
        """Return a JSON-serializable representation of the matchday.

        When ``team_name`` is provided only fixtures that include the specified
        team are included in the serialized output.
        """

        fixtures = (
            self.fixtures
            if team_name is None
            else self.fixtures_for_team(team_name)
        )

        return {
            "matchdayNumber": self.number,
            "fixtures": [fixture.to_dict() for fixture in fixtures],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Matchday:
        """Create a matchday instance from its serialized representation."""

        try:
            number = int(data.get("matchdayNumber"))
        except (TypeError, ValueError):
            raise ValueError("The serialized matchday number is invalid.") from None

        raw_fixtures = data.get("fixtures", [])
        fixtures: list[MatchFixture] = []
        if isinstance(raw_fixtures, list):
            for entry in raw_fixtures:
                if isinstance(entry, Mapping):
                    fixtures.append(MatchFixture.from_dict(entry))

        return cls(number=number, fixtures=fixtures)
