"""Repository that extracts online players from a Minecraft server log."""
from __future__ import annotations

import re
from pathlib import Path

from app.domain.models.player_session import PlayerSession
from app.domain.repositories.online_player_repository import OnlinePlayerRepository


class MinecraftLogOnlinePlayerRepository(OnlinePlayerRepository):
    """Parse the Minecraft server log to determine active player sessions."""

    _LOGIN_PATTERN = re.compile(
        r"\[(?P<time>[^\]]+)\]\s+\[Server thread/INFO\](?:\s+\[[^\]]*\])?:\s+"
        r"(?P<username>[^\[/]+)\[/"  # player name before the connection data
        r"(?P<ip>[^:]+)(?::(?P<port>\d+))?\]"  # connection endpoint
        r"\s+logged in",
    )
    _LOGOUT_PATTERNS = (
        re.compile(
            r"\[(?P<time>[^\]]+)\]\s+\[Server thread/INFO\](?:\s+\[[^\]]*\])?:\s+"
            r"(?P<username>[^\s]+)\s+lost connection:"
        ),
        re.compile(
            r"\[(?P<time>[^\]]+)\]\s+\[Server thread/INFO\](?:\s+\[[^\]]*\])?:\s+"
            r"(?P<username>[^\s]+)\s+left the game"
        ),
    )

    def __init__(self, log_path: Path) -> None:
        """Store the location of the Minecraft server log file."""

        self._log_path = log_path

    def retrieve_online_players(self) -> list[PlayerSession]:
        """Read the log file and return the players still logged in."""

        if not self._log_path.exists():
            return []

        active_sessions: dict[str, PlayerSession] = {}
        with self._log_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                login_match = self._LOGIN_PATTERN.search(line)
                if login_match:
                    active_sessions[login_match.group("username")] = PlayerSession(
                        username=login_match.group("username"),
                        ip_address=login_match.group("ip"),
                        port=self._parse_port(login_match.group("port")),
                        login_time=login_match.group("time"),
                    )
                    continue

                logout_player = self._extract_logout_player(line)
                if logout_player:
                    active_sessions.pop(logout_player, None)

        return sorted(
            active_sessions.values(),
            key=lambda session: session.login_time or "",
        )

    def _extract_logout_player(self, line: str) -> str | None:
        """Return the player name that disconnects in ``line`` when present."""

        for pattern in self._LOGOUT_PATTERNS:
            match = pattern.search(line)
            if match:
                return match.group("username")
        return None

    @staticmethod
    def _parse_port(raw_port: str | None) -> int | None:
        """Convert ``raw_port`` into an integer when available."""

        if not raw_port:
            return None
        try:
            return int(raw_port)
        except ValueError:
            return None

