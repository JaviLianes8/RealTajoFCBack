"""Tests for the top scorers PDF parser."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.domain.models.document import DocumentPage, ParsedDocument
from app.infrastructure.parsers.top_scorers_pdf_parser import TopScorersPdfParser


@dataclass
class _StubDocumentParser:
    """Simple document parser stub returning predefined lines."""

    lines: List[str]

    def parse(self, _: bytes) -> ParsedDocument:
        """Return a parsed document composed of the provided lines."""

        return ParsedDocument(pages=[DocumentPage(number=1, content=self.lines)])


def test_top_scorers_parser_extracts_entries() -> None:
    """The parser should extract scorer entries and metadata from the PDF."""

    lines = [
        "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026",
        "Jugador Equipo Grupo Partidos",
        "Jugados Goles Goles",
        "partido",
        "BOCANEGRA CAIPA, JOHN DAIRO CAFETERIA LA TACITA 2ª AFICIONADOS",
        "F-11 2 4 2,0000",
        "ARRIAGA MARTINEZ, MANUEL NEW COTTON MEKASO MCS 2ª AFICIONADOS",
        "F-11 2",
        "4 (1 de",
        "penalti) 2,0000",
        "DELEGACION ZONAL DE ARANJUEZ",
    ]

    parser = TopScorersPdfParser(document_parser=_StubDocumentParser(lines))

    table = parser.parse(b"pdf-bytes")

    assert table.title == "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026"
    assert table.category == "2ª AFICIONADOS F-11"
    assert table.season == "2025-2026"
    assert len(table.scorers) == 2

    first = table.scorers[0]
    second = table.scorers[1]

    assert first.player == "BOCANEGRA CAIPA, JOHN DAIRO"
    assert first.team == "CAFETERIA LA TACITA"
    assert first.group == "2ª AFICIONADOS F-11"
    assert first.matches_played == 2
    assert first.goals_total == 4
    assert first.goals_per_match == 2.0

    assert second.player == "ARRIAGA MARTINEZ, MANUEL"
    assert second.team == "NEW COTTON MEKASO MCS"
    assert second.penalty_goals == 1

