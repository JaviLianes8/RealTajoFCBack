"""Repository storing matchday aggregates as individual JSON files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.domain.models.matchday import Matchday
from app.domain.repositories.matchday_repository import MatchdayRepository


class JsonMatchdayRepository(MatchdayRepository):
    """Persist matchday data inside a directory of JSON files."""

    def __init__(self, directory_path: Path) -> None:
        """Initialize the repository with the directory where files are stored."""

        self._directory_path = directory_path
        self._directory_path.mkdir(parents=True, exist_ok=True)

    def save(self, matchday: Matchday) -> None:
        """Serialize and persist the provided matchday aggregate."""

        file_path = self._build_file_path(matchday.number)
        with file_path.open("w", encoding="utf-8") as output_file:
            json.dump(matchday.to_dict(), output_file, ensure_ascii=False, indent=2)

    def get(self, number: int) -> Matchday | None:
        """Load the matchday associated with ``number`` if present."""

        file_path = self._build_file_path(number)
        if not file_path.exists():
            return None
        with file_path.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)
        return Matchday.from_dict(data)

    def get_last(self) -> Matchday | None:
        """Return the matchday with the highest ordinal stored on disk."""

        highest = self._resolve_highest_matchday_number()
        if highest is None:
            return None
        return self.get(highest)

    def delete(self, number: int) -> bool:
        """Remove the JSON file for the given matchday number when present."""

        file_path = self._build_file_path(number)
        if not file_path.exists():
            return False
        file_path.unlink()
        return True

    def delete_last(self) -> bool:
        """Remove the JSON file belonging to the most recent matchday when present."""

        highest = self._resolve_highest_matchday_number()
        if highest is None:
            return False
        return self.delete(highest)

    def _build_file_path(self, number: int) -> Path:
        """Return the path where the given matchday number should be stored."""

        return self._directory_path / f"matchday_{number}.json"

    def _resolve_highest_matchday_number(self) -> Optional[int]:
        """Return the highest matchday number stored in the repository directory."""

        highest: Optional[int] = None
        pattern = re.compile(r"matchday_(\d+)\.json$")
        for file in self._directory_path.glob("matchday_*.json"):
            match = pattern.match(file.name)
            if not match:
                continue
            number = int(match.group(1))
            if highest is None or number > highest:
                highest = number
        return highest
