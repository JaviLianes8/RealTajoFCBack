"""Tests for the JSON repository persisting Real Tajo calendar data."""
from __future__ import annotations

from pathlib import Path

from app.domain.models.real_tajo_calendar import (
    KitDetails,
    RealTajoCalendar,
    RealTajoFixture,
    TeamDetails,
)
from app.infrastructure.repositories.json_real_tajo_calendar_repository import (
    JsonRealTajoCalendarRepository,
)


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Saving and loading should preserve the calendar aggregate."""

    repository = JsonRealTajoCalendarRepository(tmp_path / "calendar.json")
    calendar = RealTajoCalendar(
        team="REAL TAJO",
        competition="LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11",
        season="2025-2026",
        fixtures=[
            RealTajoFixture(
                stage="Primera Vuelta",
                round_number=1,
                date="11-10-2025",
                opponent="RACING ARANJUEZ",
                venue="home",
                home_team="REAL TAJO",
                away_team="RACING ARANJUEZ",
            )
        ],
        team_details=TeamDetails(
            contact="JUAN",
            address="28300 Aranjuez (Madrid)",
            phone="620763145",
            primary_kit=KitDetails(
                shirt_type="Lisa",
                shorts_type="Base",
                socks_type="Base",
                shirt="Azul",
                shorts="Azul",
                socks="Blancas",
            ),
            secondary_kit=KitDetails(),
        ),
    )

    repository.save(calendar)
    loaded_calendar = repository.load()

    assert loaded_calendar == calendar
