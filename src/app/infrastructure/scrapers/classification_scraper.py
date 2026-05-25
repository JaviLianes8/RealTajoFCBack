"""Parse the classification HTML page exposed by the ffmadrid portal."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def parse_classification(html: str) -> dict[str, Any]:
    """Build the JSON payload accepted by ``PUT /classification``.

    The detailed classification table is identified by the presence of
    ``<span id="{cod}_nombre">`` anchors inside each row. The summary table at
    the top of the page uses the same pattern, so rows are de-duplicated by
    team name keeping the entry with the highest number of played matches.
    """

    soup = BeautifulSoup(html, "html.parser")
    teams = _extract_teams(soup)
    last_match = _extract_last_match(soup)
    return {"metadata": _build_metadata(), "teams": teams, "last_match": last_match}


def _build_metadata() -> dict[str, Any]:
    return {
        "headers": ["Clasificación Liga"],
        "columns": [
            {"key": "team", "label": "Equipos"},
            {"key": "points", "label": "Puntos"},
            {
                "key": "matches",
                "label": "Partidos",
                "children": [
                    {"key": "played", "label": "J."},
                    {"key": "wins", "label": "G."},
                    {"key": "draws", "label": "E."},
                    {"key": "losses", "label": "P."},
                ],
            },
            {
                "key": "goals",
                "label": "Goles",
                "children": [
                    {"key": "for", "label": "F."},
                    {"key": "against", "label": "C."},
                ],
            },
            {
                "key": "recent_form",
                "label": "Últimos",
                "children": [{"key": "points", "label": "Puntos"}],
            },
            {
                "key": "sanction",
                "label": "Sanción",
                "children": [{"key": "points", "label": "Puntos"}],
            },
        ],
    }


def _extract_teams(soup: BeautifulSoup) -> list[dict[str, Any]]:
    by_team: dict[str, dict[str, Any]] = {}
    for span in soup.find_all("span", id=re.compile(r"^\d+_nombre$")):
        tr = span.find_parent("tr")
        if tr is None:
            continue
        if _belongs_to_withdrawn_section(tr):
            continue
        cells = [
            _clean(td.get_text(" ", strip=True))
            for td in tr.find_all("td")
        ]
        cells = [c for c in cells if c != ""]
        if len(cells) < 9:
            continue
        try:
            row = {
                "position": int(cells[0]),
                "team": cells[1],
                "points": int(cells[2]),
                "matches": {
                    "played": int(cells[3]),
                    "wins": int(cells[4]),
                    "draws": int(cells[5]),
                    "losses": int(cells[6]),
                },
                "goals": {"for": int(cells[7]), "against": int(cells[8])},
                "recent_form": {"points": 0},
                "sanction": {"points": _safe_int(cells[-1])},
                "raw": " ".join(cells),
            }
        except ValueError:
            continue
        existing = by_team.get(row["team"])
        if existing is None or row["matches"]["played"] > existing["matches"]["played"]:
            by_team[row["team"]] = row

    teams = list(by_team.values())
    teams.sort(key=lambda t: (-t["points"], -t["matches"]["played"], t["team"]))
    for idx, team in enumerate(teams, start=1):
        team["position"] = idx
    return teams


def _extract_last_match(soup: BeautifulSoup) -> dict[str, Any] | None:
    """Try to find the ``Jornada N (DD-MM-YYYY)`` block and its first listed game."""

    label = soup.find(string=re.compile(r"Jornada\s+\d+\s*\(\d{2}-\d{2}-\d{4}\)"))
    if label is None:
        return None
    match = re.search(r"Jornada\s+(\d+)\s*\((\d{2})-(\d{2})-(\d{4})\)", str(label))
    if not match:
        return None
    matchday = int(match.group(1))
    iso_date = f"{match.group(4)}-{match.group(3)}-{match.group(2)}"
    return {"matchday": matchday, "date": iso_date}


def _belongs_to_withdrawn_section(tr: Any) -> bool:
    table = tr.find_parent("table")
    if table is None:
        return False
    return "retirad" in table.get_text(" ", strip=True).lower()


def _clean(text: str) -> str:
    return text.replace("\xa0", "").strip()


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
