"""Application configuration helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class Settings:
    """Holds configuration values for the application."""

    data_dir: Path = Path("data")
    classification_filename: str = "classification.json"
    schedule_filename: str = "schedule.json"
    real_tajo_calendar_filename: str = "real_tajo_calendar.json"
    top_scorers_filename: str = "top_scorers.json"
    matchdays_dirname: str = "matchdays"
    app_version: str = "0.1.0"
    api_version: str = "v1"
    allowed_origins: Tuple[str, ...] = ("*",)
    max_upload_size_mb: int = 10

    @property
    def classification_path(self) -> Path:
        """Return the full path for storing classification data."""

        return self.data_dir / self.classification_filename

    @property
    def schedule_path(self) -> Path:
        """Return the full path for storing schedule data."""

        return self.data_dir / self.schedule_filename

    @property
    def real_tajo_calendar_path(self) -> Path:
        """Return the storage path for the Real Tajo calendar data."""

        return self.data_dir / self.real_tajo_calendar_filename

    @property
    def top_scorers_path(self) -> Path:
        """Return the storage path for the top scorers data."""

        return self.data_dir / self.top_scorers_filename

    @property
    def matchdays_dir(self) -> Path:
        """Return the directory used to store matchday result documents."""

        return self.data_dir / self.matchdays_dirname

    @property
    def api_prefix(self) -> str:
        """Return the URL prefix used for versioned API routes."""

        return f"/api/{self.api_version}"

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the maximum allowed upload size in bytes."""

        return self.max_upload_size_mb * 1024 * 1024


def get_settings() -> Settings:
    """Provide application settings, adapting storage for Azure deployments."""

    settings = Settings()
    upload_dir = os.getenv("UPLOAD_DIR")
    if upload_dir:
        data_dir = Path(upload_dir).expanduser()
        return replace(settings, data_dir=data_dir)

    if os.getenv("WEBSITE_INSTANCE_ID"):
        persistent_dir = Path(
            os.getenv("APP_DATA_DIR", "/home/site/data")
        ).expanduser()
        return replace(settings, data_dir=persistent_dir)

    return settings
