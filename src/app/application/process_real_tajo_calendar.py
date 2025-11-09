"""Use cases for processing and retrieving Real Tajo calendar documents."""
from __future__ import annotations

from typing import Any, Mapping

from app.domain.models.real_tajo_calendar import RealTajoCalendar
from app.domain.repositories.real_tajo_calendar_repository import (
    RealTajoCalendarRepository,
)


class ProcessRealTajoCalendarUseCase:
    """Handle ingestion and persistence of Real Tajo calendars."""

    def __init__(self, repository: RealTajoCalendarRepository) -> None:
        """Initialize the use case with its dependencies."""

        self._repository = repository

    def execute(self, data: Mapping[str, Any]) -> RealTajoCalendar:
        """Persist the provided calendar payload."""

        calendar = RealTajoCalendar.from_dict(dict(data))
        self._repository.save(calendar)
        return calendar


class RetrieveRealTajoCalendarUseCase:
    """Retrieve the last processed Real Tajo calendar if available."""

    def __init__(self, repository: RealTajoCalendarRepository) -> None:
        """Initialize the use case with the repository dependency."""

        self._repository = repository

    def execute(self) -> RealTajoCalendar | None:
        """Return the stored calendar or ``None`` when absent."""

        return self._repository.load()
