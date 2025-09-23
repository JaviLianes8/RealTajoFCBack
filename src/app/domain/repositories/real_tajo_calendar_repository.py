"""Repository interface dedicated to Real Tajo calendar data."""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.models.real_tajo_calendar import RealTajoCalendar


class RealTajoCalendarRepository(Protocol):
    """Persist and retrieve Real Tajo calendar aggregates."""

    def save(self, calendar: RealTajoCalendar) -> None:
        """Persist the provided calendar aggregate."""

    def load(self) -> Optional[RealTajoCalendar]:
        """Retrieve the stored calendar aggregate if available."""
