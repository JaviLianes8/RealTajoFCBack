"""Use cases for processing and retrieving top scorer tables."""
from __future__ import annotations

from typing import Protocol
from app.domain.models.top_scorers import TopScorersTable
from app.domain.repositories.top_scorer_repository import TopScorersRepository


class TopScorersParser(Protocol):
    """Represent a service able to extract top scorers from uploaded documents."""

    def parse(self, document_bytes: bytes) -> TopScorersTable:
        """Return the structured top scorers table contained in the document."""


class ProcessTopScorersUseCase:
    """Handle the ingestion of top scorers documents."""

    def __init__(
        self,
        parser: TopScorersParser,
        repository: TopScorersRepository,
    ) -> None:
        """Initialize the use case with its parsing and persistence dependencies."""

        self._parser = parser
        self._repository = repository

    def execute(self, document_bytes: bytes) -> TopScorersTable:
        """Parse, persist and return the extracted top scorers table."""

        table = self._parser.parse(document_bytes)
        self._repository.save(table)
        return table


class RetrieveTopScorersUseCase:
    """Retrieve the last processed top scorers table."""

    def __init__(self, repository: TopScorersRepository) -> None:
        """Initialize the use case with the repository dependency."""

        self._repository = repository

    def execute(self) -> TopScorersTable | None:
        """Return the stored top scorers table when available."""

        return self._repository.load()

