"""Use cases for processing the Real Tajo calendar document."""
from __future__ import annotations

from app.application.process_document import DocumentParser
from app.domain.models.real_tajo_calendar import RealTajoCalendar
from app.domain.repositories.real_tajo_calendar_repository import RealTajoCalendarRepository
from app.domain.services.real_tajo_calendar_extractor import RealTajoCalendarExtractorService


class ProcessRealTajoCalendarUseCase:
    """Handle ingestion of the Real Tajo calendar PDF."""

    def __init__(
        self,
        parser: DocumentParser,
        extractor: RealTajoCalendarExtractorService,
        repository: RealTajoCalendarRepository,
    ) -> None:
        """Initialize the use case with its dependencies."""

        self._parser = parser
        self._extractor = extractor
        self._repository = repository

    def execute(self, document_bytes: bytes) -> RealTajoCalendar:
        """Parse, extract and persist the Real Tajo calendar aggregate."""

        parsed_document = self._parser.parse(document_bytes)
        calendar = self._extractor.extract(parsed_document)
        self._repository.save(calendar)
        return calendar


class RetrieveRealTajoCalendarUseCase:
    """Retrieve the stored Real Tajo calendar aggregate if available."""

    def __init__(self, repository: RealTajoCalendarRepository) -> None:
        """Initialize the use case with its repository dependency."""

        self._repository = repository

    def execute(self) -> RealTajoCalendar | None:
        """Return the stored calendar aggregate or ``None`` when absent."""

        return self._repository.load()
