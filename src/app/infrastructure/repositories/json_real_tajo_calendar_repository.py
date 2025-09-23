"""Repository that persists Real Tajo calendars as JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.domain.models.real_tajo_calendar import RealTajoCalendar
from app.domain.repositories.real_tajo_calendar_repository import (
    RealTajoCalendarRepository,
)


class JsonRealTajoCalendarRepository(RealTajoCalendarRepository):
    """Persist Real Tajo calendars on disk in JSON format."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the repository with the destination file path."""

        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, calendar: RealTajoCalendar) -> None:
        """Serialize and store the calendar as JSON."""

        with self._file_path.open("w", encoding="utf-8") as output_file:
            json.dump(calendar.to_dict(), output_file, ensure_ascii=False, indent=2)

    def load(self) -> Optional[RealTajoCalendar]:
        """Load the stored calendar from disk if available."""

        if not self._file_path.exists():
            return None

        with self._file_path.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)

        if not isinstance(data, dict):
            return None

        return RealTajoCalendar.from_dict(data)
