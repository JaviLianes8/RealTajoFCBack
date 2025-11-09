"""Domain models for parsed documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping


@dataclass(frozen=True)
class DocumentPage:
    """Represents a single page extracted from an uploaded document."""

    number: int
    content: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the page."""
        return {"number": self.number, "content": list(self.content)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DocumentPage":
        """Create a document page instance from its serialized representation."""

        if not isinstance(data, Mapping):
            raise ValueError("Document page data must be a mapping.")

        number_raw = data.get("number")
        try:
            number = int(number_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError("Document page number must be an integer.") from None

        raw_content = data.get("content", [])
        if raw_content is None:
            content: Iterable[str] = []
        elif isinstance(raw_content, Iterable) and not isinstance(raw_content, (str, bytes)):
            content = (str(line) for line in raw_content)
        else:
            raise ValueError("Document page content must be an iterable of strings.")

        return cls(number=number, content=list(content))


@dataclass(frozen=True)
class ParsedDocument:
    """Represents the parsed content of an uploaded document."""

    pages: List[DocumentPage] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the document."""
        return {"pages": [page.to_dict() for page in self.pages]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ParsedDocument":
        """Create a parsed document from its serialized representation."""

        if not isinstance(data, Mapping):
            raise ValueError("Document data must be a mapping.")

        raw_pages = data.get("pages", [])
        if raw_pages is None:
            pages: list[DocumentPage] = []
        elif isinstance(raw_pages, Iterable) and not isinstance(raw_pages, (str, bytes)):
            pages = []
            for entry in raw_pages:
                if not isinstance(entry, Mapping):
                    raise ValueError(
                        "Each document page must be represented as an object."
                    )
                pages.append(DocumentPage.from_dict(entry))
        else:
            raise ValueError("Document pages must be provided as an iterable of objects.")

        return cls(pages=pages)
