"""Use cases for processing and retrieving matchday results."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.matchday_results import MatchdayResults
from app.domain.repositories.matchday_repository import MatchdayRepository


class MatchdayParser(Protocol):
    """Represent a service capable of parsing matchday results from PDF bytes."""

    def parse(self, document_bytes: bytes) -> MatchdayResults:
        """Convert raw PDF bytes into a ``MatchdayResults`` instance."""


class ProcessMatchdayResultsUseCase:
    """Handle ingestion and storage of matchday result documents."""

    def __init__(self, parser: MatchdayParser, repository: MatchdayRepository) -> None:
        """Initialize the use case with its parsing service and repository."""

        self._parser = parser
        self._repository = repository

    def execute(self, document_bytes: bytes) -> MatchdayResults:
        """Parse the uploaded document and persist the resulting matchday."""

        matchday = self._parser.parse(document_bytes)
        self._repository.save(matchday)
        return matchday


class RetrieveMatchdayUseCase:
    """Retrieve matchday results for a given round."""

    def __init__(self, repository: MatchdayRepository) -> None:
        """Initialize the use case with its repository dependency."""

        self._repository = repository

    def execute(self, matchday_number: int) -> MatchdayResults | None:
        """Return the stored results for ``matchday_number`` if present."""

        return self._repository.load(matchday_number)


class RetrieveLastMatchdayUseCase:
    """Provide access to the latest available matchday results."""

    def __init__(self, repository: MatchdayRepository) -> None:
        """Initialize the use case with its repository dependency."""

        self._repository = repository

    def execute(self) -> MatchdayResults | None:
        """Return the most recently stored matchday results if available."""

        return self._repository.load_last()
