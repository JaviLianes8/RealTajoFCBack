"""Repository protocol for storing top scorer tables."""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.models.top_scorers import TopScorersTable


class TopScorersRepository(Protocol):
    """Persist and retrieve parsed top scorers tables."""

    def save(self, table: TopScorersTable) -> None:
        """Persist the provided top scorers table."""

    def load(self) -> Optional[TopScorersTable]:
        """Retrieve the stored top scorers table if available."""

