"""Use cases for processing and retrieving classification tables."""
from __future__ import annotations

from typing import Mapping, Any

from app.domain.models.classification import ClassificationTable
from app.domain.repositories.classification_repository import ClassificationRepository


class ProcessClassificationUseCase:
    """Handle classification ingestion from JSON payloads."""

    def __init__(self, repository: ClassificationRepository) -> None:
        """Initialize the use case with the required repository dependency."""

        self._repository = repository

    def execute(self, data: Mapping[str, Any]) -> ClassificationTable:
        """Persist the provided classification data."""

        classification_table = ClassificationTable.from_dict(dict(data))
        self._repository.save(classification_table)
        return classification_table


class RetrieveClassificationUseCase:
    """Retrieve the last processed classification table."""

    def __init__(self, repository: ClassificationRepository) -> None:
        """Initialize the use case with the repository dependency."""

        self._repository = repository

    def execute(self) -> ClassificationTable | None:
        """Return the stored classification table when available."""

        return self._repository.load()

