from __future__ import annotations

from datetime import date

from app.domain.models.classification import (
    ClassificationLastMatch,
    ClassificationLastMatchTeam,
    ClassificationRow,
    ClassificationTable,
)
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


def test_extracts_rows_with_form_letters_and_concatenated_digits() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "9 REAL TAJO 0100112 P 0",
        "(*) Resultado provisional",
    )

    table = extract_classification(document)
    stats = table.rows[0].stats

    assert table.rows[0].team == "REAL TAJO"
    assert stats["points"] == 0
    assert stats["played"] == 1
    assert stats["wins"] == 0
    assert stats["draws"] == 0
    assert stats["losses"] == 1
    assert stats["goals_for"] == 1
    assert stats["goals_against"] == 2
    assert stats["last_points"] == 0
    assert stats["sanction_points"] == 0


def test_sums_multiple_form_tokens_before_decoding_stats() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1 IRT ARANJUEZ 3110021 G P 0",
    )

    table = extract_classification(document)
    stats = table.rows[0].stats

    assert stats["points"] == 3
    assert stats["played"] == 1
    assert stats["wins"] == 1
    assert stats["draws"] == 0
    assert stats["losses"] == 0
    assert stats["goals_for"] == 2
    assert stats["goals_against"] == 1
    assert stats["last_points"] == 3
    assert stats["sanction_points"] == 0


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


def test_to_dict_exposes_frontend_friendly_payload() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 0 0 0 0 0 0 0 0",
    )

    table = extract_classification(document)
    payload = table.to_dict()

    assert payload["metadata"]["columns"][0]["label"] == "Equipos"
    assert payload["metadata"]["columns"][2]["children"][0]["key"] == "played"
    assert payload["last_match"] is None
    assert payload["teams"][0]["matches"]["wins"] == 0


def test_handles_concatenated_zero_stats_sections() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 0000000 0",
    )

    table = extract_classification(document)

    assert table.rows[0].stats["points"] == 0
    assert table.rows[0].stats["losses"] == 0
    assert table.rows[0].stats["goals_against"] == 0
    assert table.rows[0].stats["sanction_points"] == 0


def test_fills_missing_trailing_stats_with_last_known_value() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 1 2 3 4 5 6 7 5",
    )

    table = extract_classification(document)

    assert table.rows[0].stats["points"] == 1
    assert table.rows[0].stats["goals_against"] == 7
    assert table.rows[0].stats["last_points"] == 5
    assert table.rows[0].stats["sanction_points"] == 5


def test_recovers_stats_when_numbers_are_concatenated() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 311003130",
    )

    table = extract_classification(document)

    stats = table.rows[0].stats
    assert stats["points"] == 3
    assert stats["played"] == 1
    assert stats["wins"] == 1
    assert stats["draws"] == 0
    assert stats["losses"] == 0
    assert stats["goals_for"] == 3
    assert stats["goals_against"] == 1
    assert stats["last_points"] == 3
    assert stats["sanction_points"] == 0


def test_prefers_goal_totals_consistent_with_match_outcomes() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "9RACING ARANJUEZ 02002210 P P 0",
    )

    table = extract_classification(document)
    stats = table.rows[0].stats

    assert stats["wins"] == 0
    assert stats["draws"] == 0
    assert stats["losses"] == 2
    assert stats["goals_for"] == 2
    assert stats["goals_against"] == 10


def test_recovers_multi_digit_statistics() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1AMERICA 1210334151070",
    )

    table = extract_classification(document)

    stats = table.rows[0].stats
    assert stats["points"] == 12
    assert stats["played"] == 10
    assert stats["wins"] == 3
    assert stats["draws"] == 3
    assert stats["losses"] == 4
    assert stats["goals_for"] == 15
    assert stats["goals_against"] == 10
    assert stats["last_points"] == 7
    assert stats["sanction_points"] == 0


def test_pads_missing_statistics_when_row_is_truncated() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 5 1",
    )

    table = extract_classification(document)
    stats = table.rows[0].stats

    assert stats["points"] == 5
    assert stats["played"] == 1
    assert stats["losses"] == 1
    assert stats["goals_for"] == 1
    assert stats["sanction_points"] == 1


def test_does_not_split_single_token_into_individual_stats() -> None:
    document = build_document(
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 121210840201050",
    )

    table = extract_classification(document)
    stats = table.rows[0].stats

    assert stats["points"] == 0
    assert stats["played"] == 0
    assert stats["wins"] == 0
    assert stats["draws"] == 0
    assert stats["losses"] == 0
    assert stats["goals_for"] == 0
    assert stats["goals_against"] == 0
    assert stats["last_points"] == 0
    assert stats["sanction_points"] == 0


def test_classification_table_roundtrip_serialization() -> None:
    row = ClassificationRow(
        position=1,
        team="ALBIRROJA",
        stats={
            "points": 3,
            "played": 1,
            "wins": 1,
            "draws": 0,
            "losses": 0,
            "goals_for": 2,
            "goals_against": 1,
            "last_points": 3,
            "sanction_points": 0,
        },
        raw="1ALBIRROJA 31002010",
    )
    last_match = ClassificationLastMatch(
        matchday=5,
        date=date(2024, 11, 2),
        home_team=ClassificationLastMatchTeam(name="REAL TAJO", score=2),
        away_team=ClassificationLastMatchTeam(name="SPLASH FC", score=3),
    )
    table = ClassificationTable(headers=["Equipos", "Puntos"], rows=[row], last_match=last_match)

    restored = ClassificationTable.from_dict(table.to_dict())

    assert restored == table


def test_extracts_last_match_with_scores() -> None:
    document = build_document(
        "Jornada 1 (11-10-2025)",
        "REAL TAJO C.F. 2 - 3 SPLASH FC",
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 0 0 0 0 0 0 0 0",
    )

    table = extract_classification(document)

    assert table.last_match is not None
    assert table.last_match.matchday == 1
    assert table.last_match.date == date(2025, 10, 11)
    assert table.last_match.home_team.name == "REAL TAJO C.F."
    assert table.last_match.home_team.score == 2
    assert table.last_match.away_team.name == "SPLASH FC"
    assert table.last_match.away_team.score == 3


def test_extracts_last_match_without_scores_returns_placeholder() -> None:
    document = build_document(
        "Jornada 1 (11-10-2025)",
        "REAL TAJO - RACING ARANJUEZ",
        "Equipos Partidos GolesÚltimosSanción",
        "PuntosJ.G.E.P.F.C. Puntos",
        "1ALBIRROJA 0 0 0 0 0 0 0 0",
    )

    table = extract_classification(document)

    assert table.last_match is not None
    assert table.last_match.home_team.name == "REAL TAJO"
    assert table.last_match.home_team.score == 0
    assert table.last_match.away_team.name == "RACING ARANJUEZ"
    assert table.last_match.away_team.score == 0
