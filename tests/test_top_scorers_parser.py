"""Tests for the Excel-based top scorers parser."""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from app.infrastructure.parsers.top_scorers_excel_parser import TopScorersExcelParser


def _build_workbook(rows: list[list[object]]) -> bytes:
    """Return workbook bytes for the provided ``rows``."""

    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_top_scorers_parser_extracts_entries_and_metadata() -> None:
    """The parser should extract metadata and scorer rows from the spreadsheet."""

    rows = [
        ["", "", "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11"],
        ["", "Temporada 2025-2026"],
        [],
        ["Jugador", "Equipo", "Grupo", "Partidos Jugados", "Goles", "Goles partido"],
        [
            "ARRIAGA MARTINEZ, MANUEL",
            "NEW COTTON MEKASO MCS",
            "2ª AFICIONADOS F-11",
            3,
            "5 (2 de penalti)",
            "1,6667",
        ],
        [
            "BOCANEGRA CAIPA, JOHN DAIRO",
            "CAFETERIA LA TACITA",
            "2ª AFICIONADOS F-11",
            3,
            4,
            "1,3333",
        ],
    ]
    document_bytes = _build_workbook(rows)

    parser = TopScorersExcelParser()

    table = parser.parse(document_bytes)

    assert table.title == "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11 Temporada 2025-2026"
    assert table.competition == "LIGA AFICIONADOS F-11"
    assert table.category == "2ª AFICIONADOS F-11"
    assert table.season == "2025-2026"
    assert len(table.scorers) == 2

    first = table.scorers[0]
    assert first.player == "ARRIAGA MARTINEZ, MANUEL"
    assert first.team == "NEW COTTON MEKASO MCS"
    assert first.group == "2ª AFICIONADOS F-11"
    assert first.matches_played == 3
    assert first.goals_total == 5
    assert first.penalty_goals == 2
    assert first.goals_per_match == 1.6667

    second = table.scorers[1]
    assert second.player == "BOCANEGRA CAIPA, JOHN DAIRO"
    assert second.goals_total == 4
    assert second.penalty_goals is None


def test_top_scorers_parser_ignores_empty_rows() -> None:
    """Rows without a player name must be ignored by the parser."""

    rows = [
        ["Encabezado", "", "Temporada 2025-2026"],
        ["Jugador", "Equipo", "Grupo", "Partidos", "Goles", "Goles partido"],
        [None, "", "", "", "", ""],
        ["Jugador Sin Equipo", "", "", "2", "1", "0,5"],
    ]
    document_bytes = _build_workbook(rows)

    parser = TopScorersExcelParser()

    table = parser.parse(document_bytes)

    assert len(table.scorers) == 1
    scorer = table.scorers[0]
    assert scorer.player == "Jugador Sin Equipo"
    assert scorer.team is None
    assert scorer.matches_played == 2
    assert scorer.goals_per_match == 0.5


def test_top_scorers_parser_requires_header() -> None:
    """The parser should fail when the header row cannot be located."""

    rows = [["Dato", "Otro"]]
    document_bytes = _build_workbook(rows)

    parser = TopScorersExcelParser()

    try:
        parser.parse(document_bytes)
    except ValueError as error:
        assert "header" in str(error).lower()
    else:
        raise AssertionError("Expected parser to raise ValueError when header is missing")
