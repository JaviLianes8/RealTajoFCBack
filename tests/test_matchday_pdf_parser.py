"""Tests for the matchday PDF parser heuristics."""
from __future__ import annotations

from app.domain.models.document import DocumentPage, ParsedDocument
from app.infrastructure.parsers.matchday_pdf_parser import MatchdayPdfParser


class _StubDocumentParser:
    """Stub document parser returning a prepared ``ParsedDocument``."""

    def __init__(self, document: ParsedDocument) -> None:
        self._document = document

    def parse(self, document_bytes: bytes) -> ParsedDocument:  # noqa: D401 - protocol compliance
        """Return the stored document regardless of the provided bytes."""

        return self._document


def test_parser_extracts_matchday_without_scores() -> None:
    """Parser should extract fixtures even when no scores are present."""

    page = DocumentPage(
        number=1,
        content=[
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Jornada 1",
            "Resultados",
            "Descansa AMERICA",
            "REAL SPORT 11-10-2025",
            "15:30",
            "REAL TAJO",
            "Campo: ENRIQUE MORENO - B - Hierba Artificial",
            "RACING ARANJUEZ 11-10-2025",
            "20:00",
            "ALBIRROJA",
            "Campo: ENRIQUE MORENO - B - Hierba Artificial",
            "LA VESPA TAPAS-CLUB",
            "ATLETICO DE ARANJUEZ 12-10-2025",
            "09:00",
            "AMG-ASESORIA JURIDICAEXCAVACIONES",
            "TAJO",
            "Campo: ENRIQUE MORENO - B - Hierba Artificial",
            "IRT ARANJUEZ 12-10-2025",
            "09:00",
            "CELTIC C.F.",
            "Campo: ENRIQUE MORENO - F - Hierba Artificial",
        ],
    )
    document = ParsedDocument(pages=[page])
    parser = MatchdayPdfParser(document_parser=_StubDocumentParser(document))

    matchday = parser.parse(b"dummy")

    assert matchday.number == 1
    assert [fixture.is_bye for fixture in matchday.fixtures] == [True, False, False, False, False]
    assert matchday.fixtures[0].home_team == "AMERICA"
    assert matchday.fixtures[1].home_team == "REAL SPORT"
    assert matchday.fixtures[1].away_team == "REAL TAJO"
    assert matchday.fixtures[1].date == "2025-10-11"
    assert matchday.fixtures[1].time == "15:30"
    assert matchday.fixtures[2].home_team == "RACING ARANJUEZ"
    assert matchday.fixtures[2].away_team == "ALBIRROJA"
    assert matchday.fixtures[2].date == "2025-10-11"
    assert matchday.fixtures[2].time == "20:00"
    assert matchday.fixtures[3].home_team == "LA VESPA TAPAS-CLUB ATLETICO DE ARANJUEZ"
    assert matchday.fixtures[3].away_team == "AMG-ASESORIA JURIDICAEXCAVACIONES TAJO"
    assert matchday.fixtures[4].home_team == "IRT ARANJUEZ"
    assert matchday.fixtures[4].away_team == "CELTIC C.F."
    assert all(fixture.home_score is None for fixture in matchday.fixtures if not fixture.is_bye)


def test_parser_extracts_scores_and_results() -> None:
    """Parser should extract scores when present in the PDF content."""

    page = DocumentPage(
        number=1,
        content=[
            "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026",
            "Jornada 3",
            "Resultados",
            "C.D. VETERANOS PANTOJA 0 - 1 RAIMON",
            "Descansa UNION CAFETERA",
            "NEW COTTON MEKASO MCS",
            "05-10-2025",
            "10:30",
            "CAFETERIA LA TACITA",
            "Campo: ENRIQUE MORENO - B - Hierba Artificial",
            "SHOTS FC",
            "3 - 2",
            "05-10-2025",
            "10:30",
            "FC. RAYO ARANJUEZ",
            "Campo: ENRIQUE MORENO - F - Hierba Artificial",
            "TABERNA CASARES / MISTER",
            "PIXEL",
            "0 - 0",
            "Campo: ENRIQUE MORENO - C - Hierba Artificial",
            "GOLDEN F.C.",
            "05-10-2025",
            "12:00",
            "ATLETICO PERU",
            "Campo: ENRIQUE MORENO - D - Hierba Artificial",
            "CHESTERFIELD UNITED",
            "ALPHA TEAM",
            "0 - 0",
            "Campo: ENRIQUE MORENO - E - Hierba Artificial",
        ],
    )
    document = ParsedDocument(pages=[page])
    parser = MatchdayPdfParser(document_parser=_StubDocumentParser(document))

    matchday = parser.parse(b"dummy")

    assert matchday.number == 3
    fixtures = [fixture for fixture in matchday.fixtures if not fixture.is_bye]
    assert fixtures[0].home_team == "C.D. VETERANOS PANTOJA"
    assert fixtures[0].away_team == "RAIMON"
    assert fixtures[0].home_score == 0
    assert fixtures[0].away_score == 1
    assert matchday.fixtures[1].is_bye
    assert fixtures[1].home_team == "NEW COTTON MEKASO MCS"
    assert fixtures[1].away_team == "CAFETERIA LA TACITA"
    assert fixtures[1].home_score is None and fixtures[1].away_score is None
    assert fixtures[2].home_team == "SHOTS FC"
    assert fixtures[2].away_team == "FC. RAYO ARANJUEZ"
    assert fixtures[2].home_score == 3 and fixtures[2].away_score == 2
    assert fixtures[2].date == "2025-10-05"
    assert fixtures[2].time == "10:30"
    assert fixtures[3].home_team == "TABERNA CASARES / MISTER"
    assert fixtures[3].away_team == "PIXEL"
    assert fixtures[3].home_score == 0 and fixtures[3].away_score == 0
    assert fixtures[4].home_team == "GOLDEN F.C."
    assert fixtures[4].away_team == "ATLETICO PERU"
    assert fixtures[4].home_score is None and fixtures[4].away_score is None
    assert fixtures[5].home_team == "CHESTERFIELD UNITED"
    assert fixtures[5].away_team == "ALPHA TEAM"
    assert fixtures[5].home_score == 0 and fixtures[5].away_score == 0


def test_parser_extracts_score_embedded_in_home_team_line() -> None:
    """Parser should capture scores appended to a team line."""

    page = DocumentPage(
        number=1,
        content=[
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Jornada 1",
            "Resultados",
            "Descansa AMERICA",
            "REAL SPORT 2 - 1",
            "11-10-2025",
            "15:30",
            "REAL TAJO",
            "Campo: ENRIQUE MORENO - B - Hierba Artificial",
        ],
    )
    document = ParsedDocument(pages=[page])
    parser = MatchdayPdfParser(document_parser=_StubDocumentParser(document))

    matchday = parser.parse(b"dummy")

    fixtures = [fixture for fixture in matchday.fixtures if not fixture.is_bye]
    assert fixtures[0].home_team == "REAL SPORT"
    assert fixtures[0].away_team == "REAL TAJO"
    assert fixtures[0].home_score == 2
    assert fixtures[0].away_score == 1
    assert fixtures[0].date == "2025-10-11"
    assert fixtures[0].time == "15:30"


def test_parser_handles_descansa_suffix_and_post_score_away_team() -> None:
    """Parser should detect byes and away teams declared after the score line."""

    page = DocumentPage(
        number=1,
        content=[
            "LIGA AFICIONADOS F-11, 3ª AFICIONADOS F-11 Temporada 2025-2026",
            "Jornada 2",
            "Resultados",
            "AMG-ASESORIA JURIDICA",
            "EXCAVACIONES",
            "TAJO Descansa",
            "REAL TAJO",
            "3 - 0",
            "19-10-2025",
            "13:40",
            "IRT ARANJUEZ",
            "Campo: ENRIQUE MORENO - F - Hierba Artificial",
        ],
    )
    document = ParsedDocument(pages=[page])
    parser = MatchdayPdfParser(document_parser=_StubDocumentParser(document))

    matchday = parser.parse(b"dummy")

    assert matchday.number == 2
    assert len(matchday.fixtures) == 2
    bye_fixture = matchday.fixtures[0]
    assert bye_fixture.is_bye
    assert bye_fixture.home_team == "AMG-ASESORIA JURIDICA EXCAVACIONES TAJO"
    match_fixture = matchday.fixtures[1]
    assert not match_fixture.is_bye
    assert match_fixture.home_team == "REAL TAJO"
    assert match_fixture.away_team == "IRT ARANJUEZ"
    assert match_fixture.home_score == 3
    assert match_fixture.away_score == 0
    assert match_fixture.date == "2025-10-19"
    assert match_fixture.time == "13:40"


def test_parser_finalizes_fixture_before_bye_block() -> None:
    """Parser should not drop the previous fixture when a bye follows immediately."""

    page = DocumentPage(
        number=1,
        content=[
            "Jornada 12",
            "Resultados",
            "TEAM A",
            "TEAM B",
            "1 - 0",
            "TEAM X Descansa",
        ],
    )
    document = ParsedDocument(pages=[page])
    parser = MatchdayPdfParser(document_parser=_StubDocumentParser(document))

    matchday = parser.parse(b"dummy")

    assert len(matchday.fixtures) == 2
    first_fixture, bye_fixture = matchday.fixtures
    assert not first_fixture.is_bye
    assert first_fixture.home_team == "TEAM A"
    assert first_fixture.away_team == "TEAM B"
    assert first_fixture.home_score == 1
    assert first_fixture.away_score == 0
    assert bye_fixture.is_bye
    assert bye_fixture.home_team == "TEAM X"
