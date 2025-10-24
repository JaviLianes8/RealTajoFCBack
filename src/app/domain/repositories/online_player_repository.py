"""Repository abstraction for retrieving online Minecraft players."""
from __future__ import annotations

from typing import Protocol

from app.domain.models.player_session import PlayerSession


class OnlinePlayerRepository(Protocol):
    """Provide access to the currently connected Minecraft players."""

    def retrieve_online_players(self) -> list[PlayerSession]:
        """Return the list of active player sessions."""

