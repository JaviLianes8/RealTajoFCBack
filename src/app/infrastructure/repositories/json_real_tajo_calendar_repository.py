"""Repository storing Real Tajo calendar aggregates as JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.domain.models.real_tajo_calendar import (
    KitDetails,
    RealTajoCalendar,
    RealTajoFixture,
    TeamDetails,
)
from app.domain.repositories.real_tajo_calendar_repository import RealTajoCalendarRepository


class JsonRealTajoCalendarRepository(RealTajoCalendarRepository):
    """Persist Real Tajo calendar aggregates on disk as JSON."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the repository with the path where data will be stored."""

        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, calendar: RealTajoCalendar) -> None:
        """Serialize and persist the calendar aggregate."""

        with self._file_path.open("w", encoding="utf-8") as output_file:
            json.dump(calendar.to_dict(), output_file, ensure_ascii=False, indent=2)

    def load(self) -> Optional[RealTajoCalendar]:
        """Load the stored calendar aggregate, returning ``None`` when absent."""

        if not self._file_path.exists():
            return None

        with self._file_path.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)

        return self._deserialize_calendar(data)

    def _deserialize_calendar(self, data: dict) -> RealTajoCalendar:
        team = data.get("team", "REAL TAJO")
        competition = data.get("competition", "")
        season = data.get("season", "")
        fixtures = [self._deserialize_fixture(item) for item in data.get("fixtures", [])]
        team_details = self._deserialize_team_details(data.get("team_details", {}))
        return RealTajoCalendar(
            team=team,
            competition=competition,
            season=season,
            fixtures=fixtures,
            team_details=team_details,
        )

    def _deserialize_fixture(self, data: dict) -> RealTajoFixture:
        stage = data.get("stage", "")
        round_number = data.get("round", 0)
        date = data.get("date", "")
        opponent = data.get("opponent", "")
        venue = data.get("venue", "")
        home_team = data.get("home_team", "")
        away_team = data.get("away_team", "")
        try:
            round_value = int(round_number)
        except (TypeError, ValueError):
            round_value = 0
        return RealTajoFixture(
            stage=str(stage),
            round_number=round_value,
            date=str(date),
            opponent=str(opponent),
            venue=str(venue),
            home_team=str(home_team),
            away_team=str(away_team),
        )

    def _deserialize_team_details(self, data: dict) -> TeamDetails:
        contact = data.get("contact")
        address = data.get("address")
        phone = data.get("phone")
        primary = self._deserialize_kit(data.get("primary_kit", {}))
        secondary = self._deserialize_kit(data.get("secondary_kit", {}))
        return TeamDetails(
            contact=str(contact) if contact is not None else None,
            address=str(address) if address is not None else None,
            phone=str(phone) if phone is not None else None,
            primary_kit=primary,
            secondary_kit=secondary,
        )

    def _deserialize_kit(self, data: dict) -> KitDetails:
        return KitDetails(
            shirt_type=self._optional_str(data.get("shirt_type")),
            shorts_type=self._optional_str(data.get("shorts_type")),
            socks_type=self._optional_str(data.get("socks_type")),
            shirt=self._optional_str(data.get("shirt")),
            shorts=self._optional_str(data.get("shorts")),
            socks=self._optional_str(data.get("socks")),
        )

    def _optional_str(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
