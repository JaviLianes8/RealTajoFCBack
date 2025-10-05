"""Domain models representing parsed matchday results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class MatchResult:
    """Represent the scoreboard of a single match within a matchday."""

    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON serializable representation of the match result."""

        return {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MatchResult":
        """Create a ``MatchResult`` from its dictionary representation."""

        return cls(
            home_team=str(data.get("home_team", "")),
            away_team=str(data.get("away_team", "")),
            home_score=_safe_int(data.get("home_score")),
            away_score=_safe_int(data.get("away_score")),
        )


@dataclass(frozen=True)
class MatchdayResults:
    """Aggregate the parsed information for a single competition matchday."""

    competition: Optional[str]
    season: Optional[str]
    matchday: int
    matches: List[MatchResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON serializable representation of the matchday results."""

        return {
            "competition": self.competition,
            "season": self.season,
            "matchday": self.matchday,
            "matches": [match.to_dict() for match in self.matches],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MatchdayResults":
        """Create ``MatchdayResults`` from their dictionary representation."""

        matches_data = data.get("matches")
        matches: List[MatchResult] = []
        if isinstance(matches_data, list):
            matches = [
                MatchResult.from_dict(item) for item in matches_data if isinstance(item, dict)
            ]

        matchday_value = data.get("matchday")
        matchday_number = _safe_int(matchday_value) or 0

        return cls(
            competition=_sanitize_optional_text(data.get("competition")),
            season=_sanitize_optional_text(data.get("season")),
            matchday=matchday_number,
            matches=matches,
        )


def _safe_int(value: object) -> Optional[int]:
    """Attempt to convert ``value`` to ``int`` returning ``None`` on failure."""

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sanitize_optional_text(value: object) -> Optional[str]:
    """Return a trimmed string representation for ``value`` when meaningful."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None
