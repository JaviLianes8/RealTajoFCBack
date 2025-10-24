"""Domain model representing an active Minecraft player session."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerSession:
    """Describe the connection details for an online Minecraft player."""

    username: str
    ip_address: str | None = None
    port: int | None = None
    login_time: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize the player session into a JSON-ready dictionary."""

        return {
            "username": self.username,
            "ipAddress": self.ip_address,
            "port": self.port,
            "loginTime": self.login_time,
        }

