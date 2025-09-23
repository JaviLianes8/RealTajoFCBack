"""Domain models describing Real Tajo's calendar extracted from competition PDFs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RealTajoKit:
    """Represent the kit information for a Real Tajo uniform."""

    shirt: Optional[str] = None
    shorts: Optional[str] = None
    socks: Optional[str] = None
    shirt_type: Optional[str] = None
    shorts_type: Optional[str] = None
    socks_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Return a JSON-serializable representation of the kit."""

        return {
            "shirt": self.shirt,
            "shorts": self.shorts,
            "socks": self.socks,
            "shirt_type": self.shirt_type,
            "shorts_type": self.shorts_type,
            "socks_type": self.socks_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Optional[str]]) -> "RealTajoKit":
        """Create a kit instance from a JSON-compatible dictionary."""

        return cls(
            shirt=data.get("shirt"),
            shorts=data.get("shorts"),
            socks=data.get("socks"),
            shirt_type=data.get("shirt_type"),
            shorts_type=data.get("shorts_type"),
            socks_type=data.get("socks_type"),
        )


@dataclass(frozen=True)
class RealTajoTeamInfo:
    """Represent the general information of the Real Tajo club."""

    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    first_kit: RealTajoKit = field(default_factory=RealTajoKit)
    second_kit: RealTajoKit = field(default_factory=RealTajoKit)

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the team information."""

        return {
            "name": self.name,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "address": self.address,
            "first_kit": self.first_kit.to_dict(),
            "second_kit": self.second_kit.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "RealTajoTeamInfo":
        """Create a team information instance from its dictionary representation."""

        first_kit_data = data.get("first_kit")
        second_kit_data = data.get("second_kit")
        first_kit = (
            RealTajoKit.from_dict(first_kit_data)
            if isinstance(first_kit_data, dict)
            else RealTajoKit()
        )
        second_kit = (
            RealTajoKit.from_dict(second_kit_data)
            if isinstance(second_kit_data, dict)
            else RealTajoKit()
        )

        return cls(
            name=str(data.get("name", "REAL TAJO")),
            contact_name=data.get("contact_name") if data else None,
            phone=data.get("phone") if data else None,
            address=data.get("address") if data else None,
            first_kit=first_kit,
            second_kit=second_kit,
        )


@dataclass(frozen=True)
class RealTajoMatch:
    """Represent a single Real Tajo fixture within the competition calendar."""

    stage: str
    matchday: int
    match_date: date
    opponent: str
    is_home: bool

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the match."""

        return {
            "stage": self.stage,
            "matchday": self.matchday,
            "date": self.match_date.isoformat(),
            "opponent": self.opponent,
            "is_home": self.is_home,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "RealTajoMatch":
        """Create a match instance from a dictionary representation."""

        raw_date = data.get("date")
        parsed_date = None
        if isinstance(raw_date, str):
            try:
                parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None

        matchday_value = data.get("matchday")
        try:
            matchday = int(matchday_value) if matchday_value is not None else 0
        except (TypeError, ValueError):
            matchday = 0

        return cls(
            stage=str(data.get("stage", "")),
            matchday=matchday,
            match_date=parsed_date or date.min,
            opponent=str(data.get("opponent", "")),
            is_home=bool(data.get("is_home", False)),
        )


@dataclass(frozen=True)
class RealTajoCalendar:
    """Aggregate the Real Tajo calendar and related club information."""

    competition: Optional[str]
    season: Optional[str]
    matches: List[RealTajoMatch] = field(default_factory=list)
    team_info: RealTajoTeamInfo = field(default_factory=lambda: RealTajoTeamInfo(name="REAL TAJO"))

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the calendar."""

        return {
            "competition": self.competition,
            "season": self.season,
            "matches": [match.to_dict() for match in self.matches],
            "team_info": self.team_info.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "RealTajoCalendar":
        """Create a calendar instance from a dictionary representation."""

        matches_data = data.get("matches") if isinstance(data, dict) else None
        matches: List[RealTajoMatch] = []
        if isinstance(matches_data, list):
            matches = [
                RealTajoMatch.from_dict(item) for item in matches_data if isinstance(item, dict)
            ]

        team_info_data = data.get("team_info") if isinstance(data, dict) else None
        team_info = (
            RealTajoTeamInfo.from_dict(team_info_data)
            if isinstance(team_info_data, dict)
            else RealTajoTeamInfo(name="REAL TAJO")
        )

        competition = data.get("competition") if isinstance(data, dict) else None
        season = data.get("season") if isinstance(data, dict) else None

        return cls(
            competition=str(competition) if competition is not None else None,
            season=str(season) if season is not None else None,
            matches=matches,
            team_info=team_info,
        )
