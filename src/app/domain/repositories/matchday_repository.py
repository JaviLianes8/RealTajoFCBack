"""Abstract repository contract for matchday aggregates."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.matchday import Matchday


class MatchdayRepository(ABC):
    """Define persistence operations available for matchday entities."""

    @abstractmethod
    def save(self, matchday: Matchday) -> None:
        """Persist the provided matchday instance."""

    @abstractmethod
    def get(self, number: int) -> Matchday | None:
        """Return the matchday identified by ``number`` if present."""

    @abstractmethod
    def get_last(self) -> Matchday | None:
        """Return the most recent matchday stored in the repository."""

    @abstractmethod
    def delete(self, number: int) -> bool:
        """Remove the matchday identified by ``number`` returning ``True`` when deleted."""

    @abstractmethod
    def delete_last(self) -> bool:
        """Remove the most recent matchday returning ``True`` when a file was deleted."""
