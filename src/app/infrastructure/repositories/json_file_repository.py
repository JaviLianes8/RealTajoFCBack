"""Repository implementation that stores parsed documents as JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.domain.models.document import ParsedDocument, DocumentPage
from app.domain.repositories.document_repository import DocumentRepository


class JsonFileRepository(DocumentRepository):
    """Persist parsed documents as JSON files on disk."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the repository with the path where data will be stored."""
        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, document: ParsedDocument) -> None:
        """Serialize and persist the parsed document."""
        with self._file_path.open("w", encoding="utf-8") as output_file:
            json.dump(document.to_dict(), output_file, ensure_ascii=False, indent=2)

    def load(self) -> Optional[ParsedDocument]:
        """Load the stored parsed document, returning ``None`` when absent."""
        if not self._file_path.exists():
            return None
        with self._file_path.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)

        pages: list[DocumentPage] = []
        for page in data.get("pages", []):
            number = page.get("number") if isinstance(page, dict) else None
            try:
                page_number = int(number) if number is not None else None
            except (TypeError, ValueError):
                page_number = None

            if page_number is None:
                continue

            raw_content = page.get("content", []) if isinstance(page, dict) else []
            if isinstance(raw_content, list):
                content = [str(line) for line in raw_content]
            elif raw_content is None:
                content = []
            else:
                content = [str(raw_content)]

            pages.append(DocumentPage(number=page_number, content=content))

        return ParsedDocument(pages=pages)
