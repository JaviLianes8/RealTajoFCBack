"""Use cases for processing and retrieving Real Tajo calendar documents."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.real_tajo_calendar import RealTajoCalendar
from app.domain.repositories.real_tajo_calendar_repository import (
    RealTajoCalendarRepository,
)


class RealTajoCalendarParser(Protocol):
    """Represent a service capable of decoding a Real Tajo calendar from PDF bytes."""

    def parse(self, document_bytes: bytes) -> RealTajoCalendar:
        """Convert raw PDF bytes into a ``RealTajoCalendar`` domain model."""


class ProcessRealTajoCalendarUseCase:
    """Handle ingestion, parsing and persistence of Real Tajo calendars."""

    def __init__(
        self,
        parser: RealTajoCalendarParser,
        repository: RealTajoCalendarRepository,
    ) -> None:
        """Initialize the use case with its dependencies."""

        self._parser = parser
        self._repository = repository

    def execute(self, document_bytes: bytes) -> RealTajoCalendar:
        """Parse the calendar PDF and persist the resulting model."""

        calendar = self._parser.parse(document_bytes)
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
