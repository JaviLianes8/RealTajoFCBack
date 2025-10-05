"""Tests for the top scorers Excel parser."""
from __future__ import annotations

import sys
from io import BytesIO
from types import ModuleType
from typing import Iterable, List

from openpyxl import Workbook

from app.infrastructure.parsers.top_scorers_excel_parser import TopScorersExcelParser


def _build_workbook(rows: Iterable[Iterable[object]]) -> bytes:
    """Return workbook bytes built from ``rows`` in the active worksheet."""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.delete_rows(1, worksheet.max_row)
    for row in rows:
        worksheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_top_scorers_parser_extracts_entries() -> None:
    """The parser should extract scorer entries and metadata from the spreadsheet."""

    rows: List[List[object]] = [
        ["LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11"],
        ["Temporada 2025-2026"],
        ["Jugador", "Equipo", "Grupo", "Partidos Jugados", "Goles", "Goles partido"],
        [
            "BOCANEGRA CAIPA, JOHN DAIRO",
            "CAFETERIA LA TACITA",
            "2ª AFICIONADOS F-11",
            3,
            "4",
            "1,3333",
        ],
        [
            "ARRIAGA MARTINEZ, MANUEL",
            "NEW COTTON MEKASO MCS",
            "2ª AFICIONADOS F-11",
            3,
            "5 (2 de penalti)",
            "1,6667",
        ],
    ]

    parser = TopScorersExcelParser()
    table = parser.parse(_build_workbook(rows))

    assert table.title == "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11"
    assert table.competition == "LIGA AFICIONADOS F-11"
    assert table.category == "2ª AFICIONADOS F-11"
    assert table.season == "2025-2026"
    assert len(table.scorers) == 2

    first = table.scorers[0]
    second = table.scorers[1]

    assert first.player == "ARRIAGA MARTINEZ, MANUEL"
    assert first.team == "NEW COTTON MEKASO MCS"
    assert first.penalty_goals == 2
    assert first.goals_per_match == 1.6667

    assert second.player == "BOCANEGRA CAIPA, JOHN DAIRO"
    assert second.goals_total == 4
    assert second.goals_per_match == 1.3333


def test_top_scorers_parser_computes_ratio_when_missing() -> None:
    """The parser should derive goals per match when the column is empty."""

    rows = [
        ["LIGA AFICIONADOS F-11"],
        ["Temporada 2025-2026"],
        ["Jugador", "Equipo", "Grupo", "Partidos", "Goles", "Goles partido"],
        ["PLAYER ONE", "TEAM", "GRUPO", 2, "4", ""],
    ]

    parser = TopScorersExcelParser()
    table = parser.parse(_build_workbook(rows))

    scorer = table.scorers[0]
    assert scorer.matches_played == 2
    assert scorer.goals_total == 4
    assert scorer.goals_per_match == 2.0


def test_top_scorers_parser_accepts_decimal_separators() -> None:
    """The parser should accept ratios expressed with dots or commas."""

    rows = [
        ["LIGA AFICIONADOS F-11"],
        ["Temporada 2025-2026"],
        ["Jugador", "Equipo", "Grupo", "Partidos", "Goles", "Goles/Partido"],
        ["PLAYER ONE", "TEAM", "GRUPO", "2", "3", "1.5"],
        ["PLAYER TWO", "TEAM", "GRUPO", "3", "3", "1,0"],
    ]

    parser = TopScorersExcelParser()
    table = parser.parse(_build_workbook(rows))

    assert len(table.scorers) == 2
    assert table.scorers[0].goals_per_match == 1.5
    assert table.scorers[1].goals_per_match == 1.0


def test_top_scorers_parser_preserves_trailing_cells_in_xls(monkeypatch) -> None:
    """The parser should keep trailing empty cells when using the XLS fallback."""

    from app.infrastructure.parsers import top_scorers_excel_parser as parser_module

    header = [
        "Jugador",
        "Equipo",
        "Grupo",
        "Partidos",
        "Goles",
        "Goles partido",
    ]
    data = ["PLAYER ONE", "TEAM", "GRUPO", 2, "4", ""]
    rows = [header, data]

    def fake_load_workbook(*_args: object, **_kwargs: object) -> None:
        raise ValueError("legacy xls")

    monkeypatch.setattr(parser_module, "load_workbook", fake_load_workbook)

    class DummySheet:
        nrows = len(rows)
        ncols = len(header)

        def row_values(self, index: int, end_colx: int | None = None) -> List[object]:
            row = list(rows[index])
            if end_colx is None:
                trimmed = list(row)
                while trimmed and trimmed[-1] in ("", None):
                    trimmed.pop()
                return trimmed
            return row[:end_colx]

    class DummyBook:
        def sheet_by_index(self, index: int) -> DummySheet:
            assert index == 0
            return DummySheet()

    class DummyXlrd:
        @staticmethod
        def open_workbook(*, file_contents: bytes) -> DummyBook:
            assert file_contents == b"fake-xls"
            return DummyBook()

    monkeypatch.setattr(parser_module, "xlrd", DummyXlrd)

    parser = parser_module.TopScorersExcelParser()
    table = parser.parse(b"fake-xls")

    assert len(table.scorers) == 1
    scorer = table.scorers[0]
    assert scorer.matches_played == 2
    assert scorer.goals_total == 4
    assert scorer.goals_per_match == 2.0


def test_import_xls_reader_prefers_supported_modules(monkeypatch) -> None:
    """The importer should skip xlrd>=2 and fall back to xlrd3 when available."""

    from app.infrastructure.parsers import top_scorers_excel_parser as parser_module

    unsupported = ModuleType("xlrd")
    unsupported.__version__ = "2.0.1"

    def _unsupported_open_workbook(**_kwargs: object) -> None:
        return None

    unsupported.open_workbook = _unsupported_open_workbook  # type: ignore[attr-defined]

    supported = ModuleType("xlrd3")
    supported.__version__ = "1.1.0"

    def _supported_open_workbook(**_kwargs: object) -> None:
        return None

    supported.open_workbook = _supported_open_workbook  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "xlrd", unsupported)
    monkeypatch.setitem(sys.modules, "xlrd3", supported)

    reader = parser_module._import_xls_reader()

    assert reader is supported
