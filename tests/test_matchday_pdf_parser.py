"""Tests for the matchday PDF parser."""
from __future__ import annotations

from app.domain.models.document import DocumentPage, ParsedDocument
from app.infrastructure.parsers.matchday_pdf_parser import MatchdayPdfParser


class _StubDocumentParser:
    """Stub parser returning a predetermined document for testing."""

    def __init__(self, document: ParsedDocument) -> None:
        self._document = document

    def parse(self, document_bytes: bytes) -> ParsedDocument:  # noqa: D401 - protocol compliance
        """Return the stored document regardless of the provided bytes."""

        return self._document


def test_matchday_parser_extracts_results_and_metadata() -> None:
    """The parser should extract competition data and match scoreboards."""

    document = ParsedDocument(
        pages=[
            DocumentPage(
                number=1,
                content=[
                    "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026",
                    "Jornada 3",
                    "Resultados",
                    "C.D. VETERANOS PANTOJA 0 - 1 RAIMON",
                    "Descansa UNION CAFETERA",
                    "SHOTS FC",
                    "3 - 2",
                    "05-10-2025",
                    "10:30",
                    "FC. RAYO ARANJUEZ",
                    "Campo: ENRIQUE MORENO - F - Hierba Artificial",
                    "PIXEL",
                    "0 - 0",
                    "05-10-2025",
                    "12:00",
                    "CHESTERFIELD UNITED",
                ],
            )
        ]
    )
    parser = MatchdayPdfParser(pdf_parser=_StubDocumentParser(document))

    result = parser.parse(b"unused")

    assert result.matchday == 3
    assert result.competition == "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11"
    assert result.season == "2025-2026"
    assert len(result.matches) == 3
    first_match = result.matches[0]
    assert first_match.home_team == "C.D. VETERANOS PANTOJA"
    assert first_match.home_score == 0
    assert first_match.away_team == "RAIMON"
    assert first_match.away_score == 1


def test_matchday_parser_handles_missing_matchday_number() -> None:
    """Parsing a document without a matchday number should raise an error."""

    document = ParsedDocument(
        pages=[
            DocumentPage(
                number=1,
                content=[
                    "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026",
                    "Resultados",
                ],
            )
        ]
    )
    parser = MatchdayPdfParser(pdf_parser=_StubDocumentParser(document))

    try:
        parser.parse(b"unused")
    except ValueError as error:
        assert str(error) == "The PDF does not specify a matchday number."
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected ValueError was not raised")
