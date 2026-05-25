"""Parse the ``NFG_VisCalendario_Vis`` page into the Real Tajo calendar JSON."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


REAL_TAJO_NAME = "REAL TAJO"


def parse_calendar(html: str, *, team_name: str = REAL_TAJO_NAME) -> dict[str, Any]:
    """Return the payload accepted by ``PUT /real-tajo/calendar``.

    Only matches in which ``team_name`` plays are kept. Rows where the team is
    listed against ``Descansa`` are skipped (no fixture to display).
    """

    soup = BeautifulSoup(html, "html.parser")
    competition, season = _extract_competition_and_season(soup)

    matches: list[dict[str, Any]] = []
    for matchday_block in _iterate_matchday_blocks(soup):
        match = _find_team_match(matchday_block, team_name=team_name)
        if match:
            matches.append(match)

    return {
        "competition": competition,
        "season": season,
        "matches": matches,
        "team_info": {"name": team_name},
    }


SEASON_PATTERN = re.compile(r"Temporada\s+(\d{4}-\d{4})", re.I)
COMPETITION_PATTERN = re.compile(r"LIGA[^|<]+?F-11[^|<]*", re.I)
JORNADA_HEADER_PATTERN = re.compile(
    r"Jornada\s+(?P<number>\d+)\s*\((?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})\)",
    re.I,
)
TIME_PATTERN = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def _extract_competition_and_season(soup: BeautifulSoup) -> tuple[str, str]:
    season = ""
    competition = ""
    for text in soup.stripped_strings:
        if not season:
            m = SEASON_PATTERN.search(text)
            if m:
                season = m.group(1)
        if not competition:
            m = COMPETITION_PATTERN.search(text)
            if m:
                competition = re.sub(r"\s+", " ", m.group(0)).strip()
        if season and competition:
            break
    return competition, season


def _iterate_matchday_blocks(soup: BeautifulSoup):
    """Yield ``(matchday_number, default_iso_date, table)`` for every Jornada table."""

    for table in soup.find_all("table"):
        header = table.get_text(" ", strip=True)
        match = JORNADA_HEADER_PATTERN.search(header)
        if not match:
            continue
        matchday_number = int(match.group("number"))
        iso_date = f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
        yield matchday_number, iso_date, table


def _find_team_match(block, *, team_name: str) -> dict[str, Any] | None:
    matchday_number, default_iso_date, table = block
    needle = team_name.upper()
    for tr in table.find_all("tr"):
        cells = [_normalize(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(cells) < 5:
            continue
        home, away = cells[0], cells[4]
        if home.upper() != needle and away.upper() != needle:
            continue
        if "DESCANSA" in (home + away).upper():
            return None
        opponent = away if home.upper() == needle else home
        is_home = home.upper() == needle
        meta_text = " ".join(cells[5:])
        date_iso, time_str, field = _extract_meta(meta_text, default_iso_date, cells)
        return {
            "stage": "Liga",
            "matchday": matchday_number,
            "date": date_iso,
            "opponent": opponent,
            "is_home": is_home,
            "time": time_str or "",
            "field": field or "",
        }
    return None


def _extract_meta(
    meta_text: str, default_iso_date: str, cells: list[str]
) -> tuple[str, str | None, str | None]:
    date_iso = default_iso_date
    explicit_date = re.search(r"(\d{2})-(\d{2})-(\d{4})", meta_text)
    if explicit_date:
        date_iso = f"{explicit_date.group(3)}-{explicit_date.group(2)}-{explicit_date.group(1)}"

    time_match = TIME_PATTERN.search(meta_text)
    time_str = (
        f"{int(time_match.group(1)):02d}:{time_match.group(2)}" if time_match else None
    )

    field: str | None = None
    if len(cells) >= 6:
        candidate = cells[5].strip()
        if candidate and "Pendiente" not in candidate:
            field = candidate
    return date_iso, time_str, field


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
