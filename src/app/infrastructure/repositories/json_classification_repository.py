"""Repository implementation that stores classification tables as JSON."""
from __future__ import annotations

import json
from pathlib import Path

from app.domain.models.classification import ClassificationTable
from app.domain.repositories.classification_repository import ClassificationRepository


class JsonClassificationRepository(ClassificationRepository):
    """Persist classification tables using a JSON file on disk."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the repository with the destination file path."""

        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, table: ClassificationTable) -> None:
        """Serialize and persist the provided classification table."""

        with self._file_path.open("w", encoding="utf-8") as output_file:
            json.dump(table.to_dict(), output_file, ensure_ascii=False, indent=2)

    def load(self) -> ClassificationTable | None:
        """Return the stored classification table when available."""

        if not self._file_path.exists():
            return None

        with self._file_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)

        return ClassificationTable.from_dict(payload)

