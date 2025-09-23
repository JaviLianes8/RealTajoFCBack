"""Tests covering the Real Tajo calendar extraction service."""
from __future__ import annotations

from app.domain.models.document import DocumentPage, ParsedDocument
from app.domain.services.real_tajo_calendar_extractor import (
    RealTajoCalendarExtractorService,
)


def build_sample_document() -> ParsedDocument:
    """Create a parsed document mimicking the provided schedule PDF."""

    page_one = DocumentPage(
        number=1,
        content=[
            "Calendario de Competiciones",
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Equipos Participantes",
            "REAL TAJO",
        ],
    )

    page_two = DocumentPage(
        number=2,
        content=[
            "Calendario de Competiciones",
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Primera Vuelta",
            "Jornada 1 (11-10-2025)",
            "NUEVO - AMERICA",
            "REAL TAJO - RACING ARANJUEZ",
            "Segunda Vuelta",
            "Jornada 10 (31-01-2026)",
            "AMERICA - NUEVO",
            "RACING ARANJUEZ - REAL TAJO",
            "Jornada 14 (21-03-2026)",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - REAL TAJO",
        ],
    )

    page_three = DocumentPage(
        number=3,
        content=[
            "Datos de interés de los equipos participantes",
            "REAL TAJO Contacto: JUAN",
            "28300 Aranjuez (Madrid)",
            "Teléfono: 620763145",
            "Primera Equipación",
            "Tipo Camiseta: Lisa Tipo Pantalón: Base Tipo Medias: Base",
            "Camiseta: Azul Pantalón: Azul Medias: Blancas",
            "2ª Equipación",
            "Camiseta: - Pantalón: - Medias: -",
        ],
    )

    return ParsedDocument(pages=[page_one, page_two, page_three])


def test_real_tajo_calendar_extraction() -> None:
    """The extractor should assemble the calendar and details for Real Tajo."""

    extractor = RealTajoCalendarExtractorService()
    calendar = extractor.extract(build_sample_document())

    assert calendar.team == "REAL TAJO"
    assert calendar.competition == "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11"
    assert calendar.season == "2025-2026"

    assert len(calendar.fixtures) == 3

    first_fixture = calendar.fixtures[0]
    assert first_fixture.stage == "Primera Vuelta"
    assert first_fixture.round_number == 1
    assert first_fixture.date == "11-10-2025"
    assert first_fixture.venue == "home"
    assert first_fixture.opponent == "RACING ARANJUEZ"

    second_fixture = calendar.fixtures[1]
    assert second_fixture.stage == "Segunda Vuelta"
    assert second_fixture.venue == "away"
    assert second_fixture.opponent == "RACING ARANJUEZ"

    third_fixture = calendar.fixtures[2]
    assert third_fixture.opponent == "AMG-ASESORIA JURIDICA- EXCAVACIONES TAJO"

    details = calendar.team_details
    assert details.contact == "JUAN"
    assert details.address == "28300 Aranjuez (Madrid)"
    assert details.phone == "620763145"
    assert details.primary_kit.shirt == "Azul"
    assert details.primary_kit.shirt_type == "Lisa"
    assert details.secondary_kit.shirt is None
