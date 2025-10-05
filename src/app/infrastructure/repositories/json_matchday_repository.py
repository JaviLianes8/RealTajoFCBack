"""JSON file repository for storing matchday results."""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.models.matchday_results import MatchdayResults
from app.domain.repositories.matchday_repository import MatchdayRepository


class JsonMatchdayRepository(MatchdayRepository):
    """Persist matchday results as individual JSON files."""

    _FILENAME_PATTERN = re.compile(r"matchday_(?P<number>\d+)\.json$")

    def __init__(self, storage_dir: Path) -> None:
        """Create the repository ensuring the storage directory exists."""

        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, matchday: MatchdayResults) -> None:
        """Persist ``matchday`` to a JSON file named after its matchday number."""

        target_path = self._storage_dir / f"matchday_{matchday.matchday}.json"
        with target_path.open("w", encoding="utf-8") as handle:
            json.dump(matchday.to_dict(), handle, ensure_ascii=False, indent=2)

    def load(self, matchday_number: int) -> MatchdayResults | None:
        """Load the stored results for ``matchday_number`` when present."""

        target_path = self._storage_dir / f"matchday_{matchday_number}.json"
        if not target_path.exists():
            return None
        with target_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return MatchdayResults.from_dict(data)

    def load_last(self) -> MatchdayResults | None:
        """Return the matchday with the highest matchday number if available."""

        matchday_files = [
            (self._extract_number(path.name), path)
            for path in self._storage_dir.glob("matchday_*.json")
        ]
        valid_files = [(number, path) for number, path in matchday_files if number is not None]
        if not valid_files:
            return None
        latest_path = max(valid_files, key=lambda item: item[0])[1]
        with latest_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return MatchdayResults.from_dict(data)

    def _extract_number(self, filename: str) -> int | None:
        """Extract the matchday number from ``filename`` when it follows the convention."""

        match = self._FILENAME_PATTERN.match(filename)
        if not match:
            return None
        return int(match.group("number"))
