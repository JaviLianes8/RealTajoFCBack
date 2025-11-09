"""Use cases for processing and retrieving top scorer tables."""
from __future__ import annotations
from typing import Any, Mapping

from app.domain.models.top_scorers import TopScorersTable
from app.domain.repositories.top_scorer_repository import TopScorersRepository


class ProcessTopScorersUseCase:
    """Handle the ingestion of top scorers payloads."""

    def __init__(self, repository: TopScorersRepository) -> None:
        """Initialize the use case with its persistence dependency."""

        self._repository = repository

    def execute(self, data: Mapping[str, Any]) -> TopScorersTable:
        """Persist and return the provided top scorers table."""

        table = TopScorersTable.from_dict(dict(data))
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

