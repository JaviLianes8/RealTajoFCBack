"""Use case for retrieving the currently connected Minecraft players."""
from __future__ import annotations

from app.domain.models.player_session import PlayerSession
from app.domain.repositories.online_player_repository import OnlinePlayerRepository


class RetrieveOnlinePlayersUseCase:
    """Expose the list of active player sessions through the domain contract."""

    def __init__(self, repository: OnlinePlayerRepository) -> None:
        """Initialize the use case with its data source dependency."""

        self._repository = repository

    def execute(self) -> list[PlayerSession]:
        """Return the online players currently known by the repository."""

        return self._repository.retrieve_online_players()

