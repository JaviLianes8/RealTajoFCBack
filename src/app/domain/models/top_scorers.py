"""Domain models representing top scorers tables extracted from PDFs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

_COLUMN_STRUCTURE: List[dict[str, Any]] = [
    {"key": "position", "label": "#"},
    {"key": "player", "label": "Jugador"},
    {"key": "team", "label": "Equipo"},
    {"key": "group", "label": "Grupo"},
    {"key": "matches_played", "label": "Partidos"},
    {"key": "goals", "label": "Goles"},
    {"key": "goals_per_match", "label": "Goles/Partido"},
]


@dataclass(frozen=True)
class TopScorerEntry:
    """Represent a single player's scoring statistics within the table."""

    player: str
    team: Optional[str]
    group: Optional[str]
    matches_played: Optional[int]
    goals_total: Optional[int]
    goals_details: Optional[str] = None
    penalty_goals: Optional[int] = None
    goals_per_match: Optional[float] = None
    raw_lines: List[str] = field(default_factory=list)

    def to_dict(self, position: int) -> dict[str, Any]:
        """Return a JSON-ready representation of the scorer entry."""

        return {
            "position": position,
            "player": self.player,
            "team": self.team,
            "group": self.group,
            "matches_played": self.matches_played,
            "goals": {
                "total": self.goals_total,
                "details": self.goals_details,
                "penalties": self.penalty_goals,
            },
            "goals_per_match": self.goals_per_match,
            "raw": list(self.raw_lines),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopScorerEntry":
        """Recreate a scorer entry from its serialized representation."""

        goals = data.get("goals") if isinstance(data, dict) else None
        return cls(
            player=str(data.get("player", "")),
            team=data.get("team"),
            group=data.get("group"),
            matches_played=_parse_optional_int(data.get("matches_played")),
            goals_total=_parse_optional_int(goals.get("total") if isinstance(goals, dict) else None),
            goals_details=goals.get("details") if isinstance(goals, dict) else None,
            penalty_goals=_parse_optional_int(goals.get("penalties") if isinstance(goals, dict) else None),
            goals_per_match=_parse_optional_float(data.get("goals_per_match")),
            raw_lines=list(data.get("raw", [])) if isinstance(data.get("raw"), list) else [],
        )


@dataclass(frozen=True)
class TopScorersTable:
    """Represent an extracted top scorers table."""

    title: Optional[str] = None
    competition: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None
    scorers: List[TopScorerEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the table."""

        rows = [scorer.to_dict(index + 1) for index, scorer in enumerate(self.scorers)]
        return {
            "metadata": {
                "title": self.title,
                "competition": self.competition,
                "category": self.category,
                "season": self.season,
                "columns": _COLUMN_STRUCTURE,
            },
            "rows": rows,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopScorersTable":
        """Rehydrate a top scorers table from its serialized form."""

        metadata = data.get("metadata") if isinstance(data, dict) else None
        rows_data = data.get("rows") if isinstance(data, dict) else []
        scorers = [TopScorerEntry.from_dict(item) for item in rows_data if isinstance(item, dict)]
        return cls(
            title=metadata.get("title") if isinstance(metadata, dict) else None,
            competition=metadata.get("competition") if isinstance(metadata, dict) else None,
            category=metadata.get("category") if isinstance(metadata, dict) else None,
            season=metadata.get("season") if isinstance(metadata, dict) else None,
            scorers=scorers,
        )


def _parse_optional_int(value: Any) -> Optional[int]:
    """Return an integer when possible otherwise ``None``."""

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_optional_float(value: Any) -> Optional[float]:
    """Return a float when possible otherwise ``None``."""

    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

