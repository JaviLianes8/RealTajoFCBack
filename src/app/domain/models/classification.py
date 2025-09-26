"""Domain models representing extracted classification tables."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, List, Optional

_COLUMN_STRUCTURE: List[dict[str, Any]] = [
    {"key": "team", "label": "Equipos"},
    {"key": "points", "label": "Puntos"},
    {
        "key": "matches",
        "label": "Partidos",
        "children": [
            {"key": "played", "label": "J."},
            {"key": "wins", "label": "G."},
            {"key": "draws", "label": "E."},
            {"key": "losses", "label": "P."},
        ],
    },
    {
        "key": "goals",
        "label": "Goles",
        "children": [
            {"key": "for", "label": "F."},
            {"key": "against", "label": "C."},
        ],
    },
    {
        "key": "recent_form",
        "label": "Últimos",
        "children": [{"key": "points", "label": "Puntos"}],
    },
    {
        "key": "sanction",
        "label": "Sanción",
        "children": [{"key": "points", "label": "Puntos"}],
    },
]


@dataclass(frozen=True)
class ClassificationLastMatchTeam:
    """Represent a team entry within the last known Real Tajo fixture."""

    name: str
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the team."""

        return {"name": self.name, "score": self.score}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationLastMatchTeam":
        """Create a team instance from its serialized representation."""

        name = str(data.get("name", "")).strip()
        score_value = data.get("score")
        try:
            score = int(score_value) if score_value is not None else 0
        except (TypeError, ValueError):
            score = 0
        return cls(name=name, score=score)


@dataclass(frozen=True)
class ClassificationLastMatch:
    """Represent the last Real Tajo fixture summary located in the classification PDF."""

    matchday: Optional[int] = None
    date: Optional[date] = None
    home_team: ClassificationLastMatchTeam = field(
        default_factory=lambda: ClassificationLastMatchTeam(name="REAL TAJO")
    )
    away_team: ClassificationLastMatchTeam = field(
        default_factory=lambda: ClassificationLastMatchTeam(name="")
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the last match summary."""

        return {
            "matchday": self.matchday,
            "date": self.date.isoformat() if self.date else None,
            "home_team": self.home_team.to_dict(),
            "away_team": self.away_team.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationLastMatch":
        """Create a last match instance from its serialized representation."""

        matchday_value = data.get("matchday") if isinstance(data, dict) else None
        try:
            matchday = int(matchday_value) if matchday_value is not None else None
        except (TypeError, ValueError):
            matchday = None

        date_value = data.get("date") if isinstance(data, dict) else None
        parsed_date: Optional[date] = None
        if isinstance(date_value, str) and date_value:
            try:
                parsed_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None

        home_team_data = data.get("home_team") if isinstance(data, dict) else None
        away_team_data = data.get("away_team") if isinstance(data, dict) else None

        home_team = (
            ClassificationLastMatchTeam.from_dict(home_team_data)
            if isinstance(home_team_data, dict)
            else ClassificationLastMatchTeam(name="REAL TAJO")
        )
        away_team = (
            ClassificationLastMatchTeam.from_dict(away_team_data)
            if isinstance(away_team_data, dict)
            else ClassificationLastMatchTeam(name="")
        )

        return cls(matchday=matchday, date=parsed_date, home_team=home_team, away_team=away_team)


@dataclass(frozen=True)
class ClassificationRow:
    """Represents a single team entry within the classification table."""

    position: int
    team: str
    stats: dict[str, int | None] = field(default_factory=dict)
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the classification row."""

        return {
            "position": self.position,
            "team": self.team,
            "points": self.stats.get("points"),
            "matches": {
                "played": self.stats.get("played"),
                "wins": self.stats.get("wins"),
                "draws": self.stats.get("draws"),
                "losses": self.stats.get("losses"),
            },
            "goals": {
                "for": self.stats.get("goals_for"),
                "against": self.stats.get("goals_against"),
            },
            "recent_form": {"points": self.stats.get("last_points")},
            "sanction": {"points": self.stats.get("sanction_points")},
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationRow":
        """Create a classification row from its serialized representation."""

        matches = data.get("matches", {})
        goals = data.get("goals", {})
        recent_form = data.get("recent_form", {})
        sanction = data.get("sanction", {})

        stats = {
            "points": data.get("points"),
            "played": matches.get("played"),
            "wins": matches.get("wins"),
            "draws": matches.get("draws"),
            "losses": matches.get("losses"),
            "goals_for": goals.get("for"),
            "goals_against": goals.get("against"),
            "last_points": recent_form.get("points"),
            "sanction_points": sanction.get("points"),
        }

        return cls(
            position=int(data["position"]),
            team=str(data["team"]),
            stats=stats,
            raw=str(data.get("raw", "")),
        )


@dataclass(frozen=True)
class ClassificationTable:
    """Represents the extracted classification section of a PDF document."""

    headers: List[str] = field(default_factory=list)
    rows: List[ClassificationRow] = field(default_factory=list)
    last_match: ClassificationLastMatch | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the classification table."""

        return {
            "metadata": {
                "headers": list(self.headers),
                "columns": _COLUMN_STRUCTURE,
            },
            "teams": [row.to_dict() for row in self.rows],
            "last_match": self.last_match.to_dict() if self.last_match else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationTable":
        """Create a classification table from its serialized representation."""

        metadata = data.get("metadata", {})
        headers = [str(header) for header in metadata.get("headers", [])]
        rows = [ClassificationRow.from_dict(item) for item in data.get("teams", [])]
        last_match_data = data.get("last_match") if isinstance(data, dict) else None
        last_match = (
            ClassificationLastMatch.from_dict(last_match_data)
            if isinstance(last_match_data, dict)
            else None
        )
        return cls(headers=headers, rows=rows, last_match=last_match)


__all__ = [
    "ClassificationRow",
    "ClassificationTable",
    "ClassificationLastMatch",
    "ClassificationLastMatchTeam",
]

