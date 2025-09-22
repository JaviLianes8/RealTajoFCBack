"""Domain models representing extracted classification tables."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

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

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the classification table."""

        return {
            "metadata": {
                "headers": list(self.headers),
                "columns": _COLUMN_STRUCTURE,
            },
            "teams": [row.to_dict() for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassificationTable":
        """Create a classification table from its serialized representation."""

        metadata = data.get("metadata", {})
        headers = [str(header) for header in metadata.get("headers", [])]
        rows = [ClassificationRow.from_dict(item) for item in data.get("teams", [])]
        return cls(headers=headers, rows=rows)


__all__ = [
    "ClassificationRow",
    "ClassificationTable",
]

