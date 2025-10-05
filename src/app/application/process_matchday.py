"""Use cases for processing and retrieving matchday data."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.matchday import Matchday
from app.domain.repositories.matchday_repository import MatchdayRepository


class MatchdayParser(Protocol):
    """Represent a service capable of parsing matchday PDFs."""

    def parse(self, document_bytes: bytes) -> Matchday:
        """Convert the supplied PDF bytes into a ``Matchday`` model."""


class ProcessMatchdayUseCase:
    """Handle ingestion, parsing and persistence of matchday documents."""

    def __init__(self, parser: MatchdayParser, repository: MatchdayRepository) -> None:
        """Initialize the use case with its collaborators."""

        self._parser = parser
        self._repository = repository

    def execute(self, document_bytes: bytes) -> Matchday:
        """Parse the PDF bytes and persist the resulting matchday."""

        matchday = self._parser.parse(document_bytes)
        self._repository.save(matchday)
        return matchday


class RetrieveMatchdayUseCase:
    """Retrieve a stored matchday identified by its ordinal number."""

    def __init__(self, repository: MatchdayRepository) -> None:
        """Initialize the use case with the repository dependency."""

        self._repository = repository

    def execute(self, number: int) -> Matchday | None:
        """Return the requested matchday or ``None`` when absent."""

        return self._repository.get(number)


class RetrieveLatestMatchdayUseCase:
    """Retrieve the most recently stored matchday if present."""

    def __init__(self, repository: MatchdayRepository) -> None:
        """Initialize the use case with the repository dependency."""

        self._repository = repository

    def execute(self) -> Matchday | None:
        """Return the latest available matchday or ``None`` when none exist."""

        return self._repository.get_last()
