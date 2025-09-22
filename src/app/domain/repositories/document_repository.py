"""Repository interfaces for storing parsed documents."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.document import ParsedDocument


class DocumentRepository(ABC):
    """Defines the behavior of a repository that stores parsed documents."""

    @abstractmethod
    def save(self, document: ParsedDocument) -> None:
        """Persist the provided parsed document."""

    @abstractmethod
    def load(self) -> Optional[ParsedDocument]:
        """Retrieve the stored parsed document if available."""
