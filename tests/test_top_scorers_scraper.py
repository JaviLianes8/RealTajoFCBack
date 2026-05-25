"""Tests for the HTML scraper that parses NFG_CMP_Goleadores."""
from __future__ import annotations

from app.infrastructure.scrapers.top_scorers_scraper import parse_top_scorers


def _render_table(player_rows: str) -> str:
    return f"""
    <html><body>
        <p>LIGA AFICIONADOS F-11, 3a AFICIONADOS F-11 Temporada 2025-2026</p>
        <table>
            <tr>
                <th>Jugador</th><th>Equipo</th><th>Grupo</th>
                <th>Partidos Jugados</th><th>Goles</th><th>Goles partido</th>
            </tr>
            {player_rows}
        </table>
    </body></html>
    """.strip()


def test_parse_top_scorers_keeps_rows_with_penalty_annotation() -> None:
    rows_html = """
        <tr>
            <td>MARIN MONTES, JUAN</td><td>REAL TAJO</td><td>3a AFICIONADOS F-11</td>
            <td>12</td><td>8 (1 de penalti)</td><td>0,6667</td>
        </tr>
        <tr>
            <td>PALLERO TUBIO, FRANCISCO JAVIER</td><td>REAL TAJO</td><td>3a AFICIONADOS F-11</td>
            <td>14</td><td>5</td><td>0,3571</td>
        </tr>
    """
    payload = parse_top_scorers(_render_table(rows_html))

    assert len(payload["rows"]) == 2
    juan, pallero = payload["rows"]

    assert juan["player"] == "MARIN MONTES, JUAN"
    assert juan["goals"] == {
        "total": 8,
        "details": "8 (1 de penalti)",
        "penalties": 1,
    }
    assert juan["goals_per_match"] == 0.6667

    assert pallero["goals"] == {"total": 5, "details": None, "penalties": 0}


def test_parse_top_scorers_skips_rows_with_non_numeric_goals() -> None:
    rows_html = """
        <tr>
            <td>PLAYER X</td><td>TEAM</td><td>GROUP</td>
            <td>10</td><td>n/a</td><td>0,5</td>
        </tr>
    """
    payload = parse_top_scorers(_render_table(rows_html))
    assert payload["rows"] == []
