"""Use cases for processing and retrieving documents."""
from __future__ import annotations

from typing import Mapping, Protocol, Any

from app.domain.models.document import ParsedDocument
from app.domain.repositories.document_repository import DocumentRepository


class DocumentParser(Protocol):
    """Represents a service capable of parsing PDF bytes into a ParsedDocument."""

    def parse(self, document_bytes: bytes) -> ParsedDocument:
        """Convert raw document bytes into a parsed document structure."""


class ProcessDocumentUseCase:
    """Handle the ingestion and persistence of uploaded documents."""

    def __init__(self, repository: DocumentRepository) -> None:
        """Initialize the use case with its required dependencies."""

        self._repository = repository

    def execute(self, document_data: Mapping[str, Any]) -> ParsedDocument:
        """Persist an already parsed document structure."""

        parsed_document = ParsedDocument.from_dict(document_data)
        self._repository.save(parsed_document)
        return parsed_document


class RetrieveDocumentUseCase:
    """Retrieve the last processed document if available."""

    def __init__(self, repository: DocumentRepository) -> None:
        """Initialize the use case with its required repository dependency."""
        self._repository = repository

    def execute(self) -> ParsedDocument | None:
        """Return the stored parsed document or ``None`` when unavailable."""
        return self._repository.load()
