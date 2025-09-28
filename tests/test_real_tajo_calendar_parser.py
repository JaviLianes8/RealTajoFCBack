"""Tests for the Real Tajo calendar PDF parser."""
from __future__ import annotations

from datetime import date

from app.domain.models.document import DocumentPage, ParsedDocument
from app.infrastructure.parsers.real_tajo_calendar_parser import (
    RealTajoCalendarPdfParser,
)


class _StubDocumentParser:
    """Stub parser returning a pre-defined ``ParsedDocument`` for testing."""

    def __init__(self, document: ParsedDocument) -> None:
        self._document = document

    def parse(self, document_bytes: bytes) -> ParsedDocument:  # noqa: D401 - protocol compliance
        """Return the stored document regardless of input."""

        return self._document


def _build_sample_document() -> ParsedDocument:
    """Build a parsed document mimicking the provided competition PDF."""

    page_one = DocumentPage(
        number=1,
        content=[
            "Calendario de Competiciones",
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Equipos Participantes",
            "AFICIONADOS F-11",
            "1.- NUEVO (1054)",
            "2.- LA VESPA TAPAS-CLUB ATLETICO DE ARANJUEZ (1028)",
            "3.- AMERICA (1052)",
            "4.- AMG-ASESORIA JURIDICA- EXCAVACIONES TAJO (1027)",
            "5.- RACING ARANJUEZ (1019)",
            "6.- CELTIC C.F. (1024)",
            "7.- REAL SPORT (1047)",
            "8.- REAL TAJO (1048)",
            "9.- IRT ARANJUEZ (1049)",
            "10.- ALBIRROJA (1050)",
            "DELEGACION ZONAL DE ARANJUEZ R.F.F.M.",
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
            "CELTIC C.F. - REAL SPORT",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - IRT ARANJUEZ",
            "ALBIRROJA - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "Jornada 2 (18-10-2025)",
            "AMERICA - ALBIRROJA",
            "RACING ARANJUEZ - NUEVO",
            "REAL SPORT - REAL TAJO",
            "IRT ARANJUEZ - CELTIC C.F.",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "Jornada 3 (25-10-2025)",
            "AMERICA - RACING ARANJUEZ",
            "NUEVO - REAL SPORT",
            "REAL TAJO - IRT ARANJUEZ",
            "CELTIC C.F. - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "ALBIRROJA - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "Jornada 4 (08-11-2025)",
            "RACING ARANJUEZ - ALBIRROJA",
            "REAL SPORT - AMERICA",
            "IRT ARANJUEZ - NUEVO",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - REAL TAJO",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - CELTIC C.F.",
            "Jornada 5 (15-11-2025)",
            "RACING ARANJUEZ - REAL SPORT",
            "AMERICA - IRT ARANJUEZ",
            "NUEVO - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "REAL TAJO - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "ALBIRROJA - CELTIC C.F.",
            "Jornada 6 (29-11-2025)",
            "REAL SPORT - ALBIRROJA",
            "IRT ARANJUEZ - RACING ARANJUEZ",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - AMERICA",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - NUEVO",
            "CELTIC C.F. - REAL TAJO",
            "Jornada 7 (13-12-2025)",
            "REAL SPORT - IRT ARANJUEZ",
            "RACING ARANJUEZ - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "AMERICA - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "NUEVO - CELTIC C.F.",
            "ALBIRROJA - REAL TAJO",
            "Jornada 8 (10-01-2026)",
            "ALBIRROJA - IRT ARANJUEZ",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - REAL SPORT",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - RACING ARANJUEZ",
            "CELTIC C.F. - AMERICA",
            "REAL TAJO - NUEVO",
            "Jornada 9 (24-01-2026)",
            "IRT ARANJUEZ - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "REAL SPORT - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "RACING ARANJUEZ - CELTIC C.F.",
            "AMERICA - REAL TAJO",
            "NUEVO - ALBIRROJA",
            "Segunda Vuelta",
            "Jornada 10 (31-01-2026)",
            "AMERICA - NUEVO",
            "RACING ARANJUEZ - REAL TAJO",
            "REAL SPORT - CELTIC C.F.",
            "IRT ARANJUEZ - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - ALBIRROJA",
            "Jornada 11 (14-02-2026)",
            "ALBIRROJA - AMERICA",
            "NUEVO - RACING ARANJUEZ",
            "REAL TAJO - REAL SPORT",
            "CELTIC C.F. - IRT ARANJUEZ",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "Jornada 12 (21-02-2026)",
            "RACING ARANJUEZ - AMERICA",
            "REAL SPORT - NUEVO",
            "IRT ARANJUEZ - REAL TAJO",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - CELTIC C.F.",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - ALBIRROJA",
            "Jornada 13 (14-03-2026)",
            "ALBIRROJA - RACING ARANJUEZ",
            "AMERICA - REAL SPORT",
            "NUEVO - IRT ARANJUEZ",
            "REAL TAJO - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "CELTIC C.F. - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "Jornada 14 (21-03-2026)",
            "REAL SPORT - RACING ARANJUEZ",
            "IRT ARANJUEZ - AMERICA",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - NUEVO",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - REAL TAJO",
            "CELTIC C.F. - ALBIRROJA",
            "Jornada 15 (11-04-2026)",
            "ALBIRROJA - REAL SPORT",
            "RACING ARANJUEZ - IRT ARANJUEZ",
            "AMERICA - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "NUEVO - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "REAL TAJO - CELTIC C.F.",
            "Jornada 16 (18-04-2026)",
            "IRT ARANJUEZ - REAL SPORT",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - RACING ARANJUEZ",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - AMERICA",
            "CELTIC C.F. - NUEVO",
            "REAL TAJO - ALBIRROJA",
            "Jornada 17 (09-05-2026)",
            "IRT ARANJUEZ - ALBIRROJA",
            "REAL SPORT - LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ",
            "RACING ARANJUEZ - AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO",
            "AMERICA - CELTIC C.F.",
            "NUEVO - REAL TAJO",
            "Jornada 18 (16-05-2026)",
            "LA VESPA TAPAS-CLUB ATLETICO DE",
            "ARANJUEZ - IRT ARANJUEZ",
            "AMG-ASESORIA JURIDICA- EXCAVACIONES",
            "TAJO - REAL SPORT",
            "CELTIC C.F. - RACING ARANJUEZ",
            "REAL TAJO - AMERICA",
            "ALBIRROJA - NUEVO",
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
            "Camiseta: - Pantalon: - Medias: -",
        ],
    )

    return ParsedDocument(pages=[page_one, page_two, page_three])


def test_parser_extracts_real_tajo_calendar() -> None:
    """Ensure the parser extracts the Real Tajo schedule and team information."""

    document = _build_sample_document()
    parser = RealTajoCalendarPdfParser(document_parser=_StubDocumentParser(document))

    calendar = parser.parse(b"binary")

    assert calendar.competition == "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11"
    assert calendar.season == "2025-2026"
    assert len(calendar.matches) == 18

    first_match = calendar.matches[0]
    assert first_match.stage == "Primera Vuelta"
    assert first_match.matchday == 1
    assert first_match.match_date == date(2025, 10, 11)
    assert first_match.is_home is True
    assert first_match.opponent == "RACING ARANJUEZ"

    last_match = calendar.matches[-1]
    assert last_match.stage == "Segunda Vuelta"
    assert last_match.matchday == 18
    assert last_match.match_date == date(2026, 5, 16)
    assert last_match.is_home is True
    assert last_match.opponent == "AMERICA"

    team_info = calendar.team_info
    assert team_info.name == "REAL TAJO"
    assert team_info.contact_name == "JUAN"
    assert team_info.phone == "620763145"
    assert team_info.address == "28300 Aranjuez (Madrid)"
    assert team_info.first_kit.shirt == "Azul"
    assert team_info.first_kit.shirt_type == "Lisa"
    assert team_info.first_kit.socks == "Blancas"


def test_parser_handles_inline_matchdays_and_multiple_matches_per_line() -> None:
    """Validate the parser when matchdays and fixtures are condensed in a single line."""

    document = ParsedDocument(
        pages=[
            DocumentPage(
                number=1,
                content=[
                    "Calendario de Competiciones",
                    "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
                    "Equipos Participantes",
                    "AFICIONADOS F-11",
                    "1.- NUEVO (1054)",
                    "2.- RACING ARANJUEZ (1019)",
                    "3.- REAL TAJO (1048)",
                    "4.- AMERICA (1052)",
                    "5.- REAL SPORT (1047)",
                ],
            ),
            DocumentPage(
                number=2,
                content=[
                    "Primera Vuelta Jornada 1 (11-10-2025) NUEVO - AMERICA REAL TAJO - RACING ARANJUEZ",
                    "Segunda Vuelta Jornada 10 (31-01-2026) RACING ARANJUEZ - REAL TAJO REAL SPORT - CELTIC C.F.",
                ],
            ),
            DocumentPage(
                number=3,
                content=[
                    "Datos de interés de los equipos participantes",
                    "REAL TAJO Contacto: JUAN",
                    "Teléfono: 620763145",
                    "Primera Equipación",
                    "Tipo Camiseta: Lisa Tipo Pantalón: Base Tipo Medias: Base",
                    "Camiseta: Azul Pantalón: Azul Medias: Blancas",
                ],
            ),
        ]
    )

    parser = RealTajoCalendarPdfParser(document_parser=_StubDocumentParser(document))

    calendar = parser.parse(b"inline")

    assert len(calendar.matches) == 2

    first_match, second_match = calendar.matches
    assert first_match.stage == "Primera Vuelta"
    assert first_match.matchday == 1
    assert first_match.is_home is True
    assert first_match.opponent == "RACING ARANJUEZ"

    assert second_match.stage == "Segunda Vuelta"
    assert second_match.matchday == 10
    assert second_match.is_home is False
    assert second_match.opponent == "RACING ARANJUEZ"


def test_parser_supports_multiline_team_names_in_participants_section() -> None:
    """Ensure the parser recognises team names split across multiple lines."""

    document = ParsedDocument(
        pages=[
            DocumentPage(
                number=1,
                content=[
                    "Calendario de Competiciones",
                    "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
                    "Equipos Participantes",
                    "1.- LA VESPA TAPAS-CLUB ATLETICO DE",
                    "ARANJUEZ (1001)",
                    "2.- AMG-ASESORIA JURIDICA- EXCAVACIONES",
                    "TAJO (1002)",
                    "3.- IRT ARANJUEZ (1003)",
                    "4.- REAL TAJO (1004)",
                ],
            ),
            DocumentPage(
                number=2,
                content=[
                    "Primera Vuelta",
                    "Jornada 1 (11-10-2025)",
                    "LA VESPA TAPAS-CLUB ATLETICO DE",
                    "ARANJUEZ - REAL TAJO",
                    "Jornada 2 (18-10-2025)",
                    "REAL TAJO - AMG-ASESORIA JURIDICA- EXCAVACIONES",
                    "TAJO",
                    "Jornada 3 (25-10-2025)",
                    "IRT ARANJUEZ - REAL TAJO",
                ],
            ),
        ]
    )

    parser = RealTajoCalendarPdfParser(document_parser=_StubDocumentParser(document))

    calendar = parser.parse(b"multiline")

    opponents = {match.opponent for match in calendar.matches}
    assert opponents == {
        "LA VESPA TAPAS-CLUB ATLETICO DE ARANJUEZ",
        "AMG-ASESORIA JURIDICA- EXCAVACIONES TAJO",
        "IRT ARANJUEZ",
    }
