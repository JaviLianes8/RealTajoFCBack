"""Domain models for parsed documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class DocumentPage:
    """Represents a single page extracted from an uploaded document."""

    number: int
    content: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the page."""
        return {"number": self.number, "content": list(self.content)}


@dataclass(frozen=True)
class ParsedDocument:
    """Represents the parsed content of an uploaded document."""

    pages: List[DocumentPage] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the document."""
        return {"pages": [page.to_dict() for page in self.pages]}
