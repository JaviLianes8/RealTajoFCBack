from __future__ import annotations

from app.domain.models.document import DocumentPage, ParsedDocument
from app.domain.services.classification_extractor import extract_classification


def build_document(*lines: str) -> ParsedDocument:
    return ParsedDocument(pages=[DocumentPage(number=1, content=list(lines))])


def test_extracts_rows_when_team_and_stats_are_concatenated() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 0 0 0 0 0 0 0 0",
        "2 AMERICA 1 0 0 1 2 3 4 5",
        "(*) Resultado provisional",
    )

    table = extract_classification(document)

    assert len(table.rows) == 2
    assert table.rows[0].team == "ALBIRROJA"
    assert table.rows[0].stats["points"] == 0
    assert table.rows[1].team == "AMERICA"
    assert table.rows[1].stats["losses"] == 2


def test_merges_multi_line_rows_before_parsing() -> None:
    document = build_document(
        "Equipos Partidos Goles Últimos Sanción",
        "Puntos J. G. E. P. F. C. Puntos",
        "1 ALBIRROJA",
        "0 0 0 0 0 0 0 0",
        "2CELTIC C.F. 3 2 1 4 5 6 7 8",
        "(*) Resultado provisional",
    )

    table = extract_classification(document)

    assert len(table.rows) == 2
    assert table.rows[0].team == "ALBIRROJA"
    assert table.rows[0].stats["goals_against"] == 0
    assert table.rows[1].team == "CELTIC C.F."
    assert table.rows[1].stats["played"] == 2
