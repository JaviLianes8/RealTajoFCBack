"""Repository contract for persisting Real Tajo calendars."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.real_tajo_calendar import RealTajoCalendar


class RealTajoCalendarRepository(Protocol):
    """Define the operations required to persist Real Tajo calendar data."""

    def save(self, calendar: RealTajoCalendar) -> None:
        """Persist the provided Real Tajo calendar."""

    def load(self) -> RealTajoCalendar | None:
        """Retrieve the stored Real Tajo calendar if any is available."""
