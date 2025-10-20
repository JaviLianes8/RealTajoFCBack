"""Domain models describing matchday fixtures and results."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping


_TEAM_NAME_SEPARATOR_CHARS = " -,:\u2013"


def _normalize_team_name(name: str | None) -> str:
    """Return a normalized version of ``name`` for case-insensitive comparisons."""

    if name is None:
        return ""
    return " ".join(name.strip().casefold().split())


def _extract_opponent_segment(name: str | None, team_name: str) -> str | None:
    """Return the opponent segment when ``team_name`` is embedded in ``name``."""

    if not name:
        return None

    pattern = re.compile(re.escape(team_name), flags=re.IGNORECASE)
    match = pattern.search(name)
    if not match:
        return None

    before = name[: match.start()].strip(_TEAM_NAME_SEPARATOR_CHARS)
    after = name[match.end() :].strip(_TEAM_NAME_SEPARATOR_CHARS)

    candidates = [segment for segment in (before, after) if _is_meaningful_opponent(segment)]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _is_meaningful_opponent(segment: str | None) -> bool:
    """Return ``True`` when ``segment`` resembles a valid opponent name."""

    if not segment:
        return False

    normalized = _normalize_team_name(segment)
    if not normalized:
        return False
    if " " in normalized:
        return True

    letters = [character for character in normalized if character.isalpha()]
    return len(letters) >= 3


@dataclass(frozen=True)
class MatchFixture:
    """Represent a single fixture, optionally including the final score."""

    home_team: str
    away_team: str | None
    home_score: int | None = None
    away_score: int | None = None
    is_bye: bool = False
    date: str | None = None
    time: str | None = None

    def to_dict(self, team_name: str | None = None) -> dict[str, Any]:
        """Return a JSON-serializable representation of the fixture."""

        if team_name and not self.is_bye:
            serialized = self._serialize_for_team(team_name)
        else:
            serialized = {
                "homeTeam": self.home_team,
                "awayTeam": self.away_team,
            }

        return {
            "homeTeam": serialized.get("homeTeam"),
            "awayTeam": serialized.get("awayTeam"),
            "homeScore": self.home_score,
            "awayScore": self.away_score,
            "isBye": self.is_bye,
            "date": self.date,
            "time": self.time,
        }

    def _serialize_for_team(self, team_name: str) -> dict[str, str | None]:
        """Return team labels adjusted so ``team_name`` appears as a side."""

        normalized_target = _normalize_team_name(team_name)
        home_contains = normalized_target in _normalize_team_name(self.home_team)
        away_contains = normalized_target in _normalize_team_name(self.away_team)

        if home_contains and not away_contains:
            opponent = _extract_opponent_segment(self.home_team, team_name)
            if opponent:
                return {
                    "homeTeam": opponent,
                    "awayTeam": team_name,
                }
            return {
                "homeTeam": self.home_team,
                "awayTeam": self.away_team,
            }
        if away_contains and not home_contains:
            opponent = _extract_opponent_segment(self.away_team, team_name)
            return {
                "homeTeam": opponent or self.home_team,
                "awayTeam": team_name,
            }
        if home_contains and away_contains:
            return {
                "homeTeam": team_name,
                "awayTeam": team_name,
            }
        return {
            "homeTeam": self.home_team,
            "awayTeam": self.away_team,
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
        date_value = data.get("date")
        time_value = data.get("time")
        date = str(date_value).strip() if date_value is not None else None
        time = str(time_value).strip() if time_value is not None else None

        return cls(
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            is_bye=is_bye,
            date=date,
            time=time,
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
            "fixtures": [
                fixture.to_dict(team_name=team_name) for fixture in fixtures
            ],
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
