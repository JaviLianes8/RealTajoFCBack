"""Repository interfaces for storing parsed documents."""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.models.document import ParsedDocument


class DocumentRepository(Protocol):
    """Persist and retrieve parsed documents."""

    def save(self, document: ParsedDocument) -> None:
        """Persist the provided parsed document."""

    def load(self) -> Optional[ParsedDocument]:
        """Retrieve the stored parsed document if available."""
