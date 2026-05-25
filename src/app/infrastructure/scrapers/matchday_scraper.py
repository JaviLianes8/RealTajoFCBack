"""Parse the matchday detail page exposed by ``NFG_CmpJornada``."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def parse_matchday(html: str) -> dict[str, Any]:
    """Build the JSON payload accepted by ``POST /matchdays/last``.

    Expected output shape::

        {
            "matchdayNumber": int,
            "fixtures": [
                {"homeTeam": str, "awayTeam": str,
                 "homeScore": int|None, "awayScore": int|None,
                 "isBye": bool, "date": "YYYY-MM-DD", "time": "HH:MM"}
            ],
        }
    """

    soup = BeautifulSoup(html, "html.parser")
    matchday_number, iso_date = _extract_matchday_header(soup)
    fixtures = _extract_fixtures(soup, default_date=iso_date)
    return {"matchdayNumber": matchday_number, "fixtures": fixtures}


def _extract_matchday_header(soup: BeautifulSoup) -> tuple[int, str | None]:
    label = soup.find(string=re.compile(r"Jornada\s+\d+", re.I))
    if label is None:
        return 0, None
    match = re.search(
        r"Jornada\s+(\d+)(?:\s*\((\d{2})-(\d{2})-(\d{4})\))?", str(label), re.I
    )
    if not match:
        return 0, None
    matchday_number = int(match.group(1))
    iso_date: str | None = None
    if match.group(2):
        iso_date = f"{match.group(4)}-{match.group(3)}-{match.group(2)}"
    return matchday_number, iso_date


def _extract_fixtures(
    soup: BeautifulSoup, *, default_date: str | None
) -> list[dict[str, Any]]:
    """Each fixture row contains two team names and a score in between.

    The federation portal uses one of two layouts: the summary table at the
    top of the classification page (no time information) or the dedicated
    matchday view with `<a>` anchors for each team. This parser handles both:
    we look for any element/text that matches the pattern ``TEAM N-M TEAM``
    (or ``TEAM N - M TEAM``), plus rows containing the literal ``Descansa``.
    """

    fixtures: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row_text, row_node in _iterate_score_rows(soup):
        fixture = _parse_score_row(row_text, default_date=default_date)
        if fixture is None:
            continue
        time = _extract_time_near(row_node)
        if time:
            fixture["time"] = time
        key = f"{fixture['homeTeam']}|{fixture['awayTeam']}"
        if key in seen:
            continue
        seen.add(key)
        fixtures.append(fixture)

    bye_text = _find_bye_team(soup)
    if bye_text:
        fixtures.append(
            {
                "homeTeam": bye_text,
                "awayTeam": None,
                "homeScore": None,
                "awayScore": None,
                "isBye": True,
                "date": default_date,
                "time": None,
            }
        )
    return fixtures


SCORE_PATTERN = re.compile(
    r"^(?P<home>.+?)\s+(?P<hs>\d{1,2})\s*-\s*(?P<as>\d{1,2})\s+(?P<rest>.+)$"
)
DATE_PATTERN = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
TIME_PATTERN = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def _iterate_score_rows(soup: BeautifulSoup):
    """Yield (joined_text, node) for every row whose visible text contains a score."""

    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True).replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        if re.search(r"\b\d{1,2}\s*-\s*\d{1,2}\b", text):
            yield text, tr


def _parse_score_row(text: str, *, default_date: str | None) -> dict[str, Any] | None:
    match = SCORE_PATTERN.match(text)
    if not match:
        return None
    home = _clean_team(match.group("home"))
    rest = match.group("rest")
    date_iso, time_str, away_text = _peel_date_time(rest)
    away = _clean_team(away_text)
    if not home or not away:
        return None
    return {
        "homeTeam": home,
        "awayTeam": away,
        "homeScore": int(match.group("hs")),
        "awayScore": int(match.group("as")),
        "isBye": False,
        "date": date_iso or default_date,
        "time": time_str,
    }


def _peel_date_time(text: str) -> tuple[str | None, str | None, str]:
    """Strip any leading ``DD-MM-YYYY`` and ``HH:MM`` from ``text``."""

    date_iso: str | None = None
    time_str: str | None = None
    remaining = text

    date_match = DATE_PATTERN.match(remaining)
    if date_match:
        date_iso = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
        remaining = remaining[date_match.end():].lstrip()

    time_match = TIME_PATTERN.match(remaining)
    if time_match:
        time_str = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        remaining = remaining[time_match.end():].lstrip()

    return date_iso, time_str, remaining


def _extract_time_near(node: Any) -> str | None:
    text = node.get_text(" ", strip=True)
    match = TIME_PATTERN.search(text)
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _find_bye_team(soup: BeautifulSoup) -> str | None:
    label = soup.find(string=re.compile(r"Descansa", re.I))
    if label is None:
        return None
    container = label.parent
    if container is None:
        return None
    text = container.get_text(" ", strip=True)
    match = re.search(r"Descansa\s*[-:]?\s*(.+?)(?:$|\s{2,})", text, re.I)
    if not match:
        return None
    return _clean_team(match.group(1))


def _clean_team(value: str) -> str:
    cleaned = value.replace("\xa0", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -·.,;")
