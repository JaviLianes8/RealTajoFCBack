"""Repository abstractions for persisting classification tables."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.classification import ClassificationTable


class ClassificationRepository(Protocol):
    """Persist and retrieve classification tables."""

    def save(self, table: ClassificationTable) -> None:
        """Persist the provided classification table."""

    def load(self) -> ClassificationTable | None:
        """Return the stored classification table when available."""

