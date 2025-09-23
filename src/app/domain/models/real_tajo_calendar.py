"""Domain models representing the Real Tajo calendar document."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class KitDetails:
    """Describe the kit configuration for a team."""

    shirt_type: str | None = None
    shorts_type: str | None = None
    socks_type: str | None = None
    shirt: str | None = None
    shorts: str | None = None
    socks: str | None = None

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the kit."""

        return {
            "shirt_type": self.shirt_type,
            "shorts_type": self.shorts_type,
            "socks_type": self.socks_type,
            "shirt": self.shirt,
            "shorts": self.shorts,
            "socks": self.socks,
        }


@dataclass(frozen=True)
class TeamDetails:
    """Represent the general information of Real Tajo."""

    contact: str | None = None
    address: str | None = None
    phone: str | None = None
    primary_kit: KitDetails = field(default_factory=KitDetails)
    secondary_kit: KitDetails = field(default_factory=KitDetails)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the team details."""

        return {
            "contact": self.contact,
            "address": self.address,
            "phone": self.phone,
            "primary_kit": self.primary_kit.to_dict(),
            "secondary_kit": self.secondary_kit.to_dict(),
        }


@dataclass(frozen=True)
class RealTajoFixture:
    """Represent a single Real Tajo fixture within the calendar."""

    stage: str
    round_number: int
    date: str
    opponent: str
    venue: str
    home_team: str
    away_team: str

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the fixture."""

        return {
            "stage": self.stage,
            "round": self.round_number,
            "date": self.date,
            "opponent": self.opponent,
            "venue": self.venue,
            "home_team": self.home_team,
            "away_team": self.away_team,
        }


@dataclass(frozen=True)
class RealTajoCalendar:
    """Aggregate the calendar and team details extracted from the document."""

    team: str
    competition: str
    season: str
    fixtures: List[RealTajoFixture] = field(default_factory=list)
    team_details: TeamDetails = field(default_factory=TeamDetails)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the calendar."""

        return {
            "team": self.team,
            "competition": self.competition,
            "season": self.season,
            "fixtures": [fixture.to_dict() for fixture in self.fixtures],
            "team_details": self.team_details.to_dict(),
        }
