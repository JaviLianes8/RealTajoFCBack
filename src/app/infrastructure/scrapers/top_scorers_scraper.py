"""Parse the ``NFG_CMP_Goleadores`` page into the back's expected JSON."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def parse_top_scorers(html: str) -> dict[str, Any]:
    """Build the payload accepted by ``PUT /top-scorers``."""

    soup = BeautifulSoup(html, "html.parser")
    competition, season = _extract_competition_and_season(soup)
    rows = _extract_rows(soup)
    return {
        "metadata": _build_metadata(competition=competition, season=season),
        "rows": rows,
    }


def _build_metadata(*, competition: str | None, season: str | None) -> dict[str, Any]:
    return {
        "title": "Goleadores",
        "competition": competition,
        "category": "Senior",
        "season": season,
        "columns": [
            {"key": "position", "label": "#"},
            {"key": "player", "label": "Jugador"},
            {"key": "team", "label": "Equipo"},
            {"key": "group", "label": "Grupo"},
            {"key": "matches_played", "label": "Partidos"},
            {"key": "goals", "label": "Goles"},
            {"key": "goals_per_match", "label": "Goles/Partido"},
        ],
    }


SEASON_PATTERN = re.compile(r"Temporada\s+(\d{4}-\d{4})", re.I)
COMPETITION_PATTERN = re.compile(r"LIGA[^|]+?F-11[^|]*", re.I)


def _extract_competition_and_season(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    season: str | None = None
    competition: str | None = None
    for text in soup.stripped_strings:
        if not season:
            season_match = SEASON_PATTERN.search(text)
            if season_match:
                season = season_match.group(1)
        if not competition:
            competition_match = COMPETITION_PATTERN.search(text)
            if competition_match:
                competition = re.sub(r"\s+", " ", competition_match.group(0)).strip()
        if season and competition:
            break
    return competition, season


def _extract_rows(soup: BeautifulSoup) -> list[dict[str, Any]]:
    target = _find_target_table(soup)
    if target is None:
        return []

    rows: list[dict[str, Any]] = []
    for tr in target.find_all("tr"):
        cells = [_clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        cells = [c for c in cells if c != ""]
        if len(cells) < 5:
            continue
        try:
            matches_played = int(cells[-3])
            goals_total = int(cells[-2])
            goals_per_match = _parse_decimal(cells[-1])
        except ValueError:
            continue
        player = cells[0]
        team = cells[1] if len(cells) >= 5 else ""
        group = cells[2] if len(cells) >= 5 else ""
        rows.append(
            {
                "position": len(rows) + 1,
                "player": player,
                "team": team,
                "group": group,
                "matches_played": matches_played,
                "goals": {"total": goals_total, "details": None, "penalties": 0},
                "goals_per_match": goals_per_match,
                "raw": [" ".join(cells)],
            }
        )
    return rows


def _find_target_table(soup: BeautifulSoup) -> Any:
    for table in soup.find_all("table"):
        header_text = " ".join(
            cell.get_text(" ", strip=True) for cell in table.find_all("th")
        ).lower()
        if "jugador" in header_text and "goles" in header_text:
            return table
    return None


def _clean(text: str) -> str:
    return text.replace("\xa0", "").strip()


def _parse_decimal(text: str) -> float:
    cleaned = text.replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
