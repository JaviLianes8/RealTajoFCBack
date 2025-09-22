"""Use cases for processing and retrieving classification tables."""
from __future__ import annotations

from typing import Protocol

from app.application.process_document import DocumentParser
from app.domain.models.classification import ClassificationTable
from app.domain.models.document import ParsedDocument
from app.domain.repositories.classification_repository import ClassificationRepository


class ClassificationExtractor(Protocol):
    """Represent a service able to extract classification data from documents."""

    def extract(self, document: ParsedDocument) -> ClassificationTable:
        """Return the structured classification table present in ``document``."""


class ProcessClassificationUseCase:
    """Handle classification ingestion from raw PDF bytes."""

    def __init__(
        self,
        parser: DocumentParser,
        extractor: ClassificationExtractor,
        repository: ClassificationRepository,
    ) -> None:
        """Initialize the use case with its required collaborators."""

        self._parser = parser
        self._extractor = extractor
        self._repository = repository

    def execute(self, document_bytes: bytes) -> ClassificationTable:
        """Parse, extract and persist the classification table contained in a PDF."""

        parsed_document = self._parser.parse(document_bytes)
        classification_table = self._extractor.extract(parsed_document)
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

