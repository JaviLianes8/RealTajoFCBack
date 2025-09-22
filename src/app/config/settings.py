"""Application configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Holds configuration values for the application."""

    data_dir: Path = Path("data")
    classification_filename: str = "classification.json"
    schedule_filename: str = "schedule.json"

    @property
    def classification_path(self) -> Path:
        """Return the full path for storing classification data."""
        return self.data_dir / self.classification_filename

    @property
    def schedule_path(self) -> Path:
        """Return the full path for storing schedule data."""
        return self.data_dir / self.schedule_filename


def get_settings() -> Settings:
    """Provide the default application settings."""
    return Settings()
