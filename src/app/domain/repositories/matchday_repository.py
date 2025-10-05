"""Repository abstraction for storing matchday results."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.matchday_results import MatchdayResults


class MatchdayRepository(Protocol):
    """Define the contract for persisting matchday results."""

    def save(self, matchday: MatchdayResults) -> None:
        """Persist the provided ``matchday`` data."""

    def load(self, matchday_number: int) -> MatchdayResults | None:
        """Retrieve the stored results for ``matchday_number`` if available."""

    def load_last(self) -> MatchdayResults | None:
        """Return the most recent matchday results available."""
