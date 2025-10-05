"""Excel parser for extracting top scorers tables."""
from __future__ import annotations

import re
from importlib import import_module
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional

from openpyxl import load_workbook

def _parse_version_tuple(raw_version: str) -> tuple[int, ...]:
    """Return a tuple with the numeric portions of ``raw_version``."""

    parts = re.findall(r"\d+", raw_version)
    return tuple(int(part) for part in parts)


def _import_xls_reader() -> Any | None:
    """Return a module capable of reading legacy XLS spreadsheets when available."""

    for module_name in ("xlrd", "xlrd3"):
        try:  # pragma: no cover - depends on optional runtime dependencies
            module = import_module(module_name)
        except Exception:  # pragma: no cover - module not installed or unusable
            continue

        version = _parse_version_tuple(getattr(module, "__version__", ""))
        if module_name == "xlrd" and version >= (2, 0, 0):
            # xlrd >= 2 removed support for legacy XLS files, fall back to xlrd3.
            continue

        if hasattr(module, "open_workbook"):
            return module

    return None


xlrd = _import_xls_reader()

from app.application.process_top_scorers import TopScorersParser
from app.domain.models.top_scorers import TopScorerEntry, TopScorersTable


_HEADER_ALIASES: Dict[str, set[str]] = {
    "player": {"jugador"},
    "team": {"equipo"},
    "group": {"grupo"},
    "matches": {"partidos", "partidos jugados"},
    "goals": {"goles"},
    "ratio": {"goles partido", "goles/partido", "goles por partido"},
}
_PENALTIES_RE = re.compile(r"(\d+)\s*de\s*penalti", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+")


def _stringify(value: Any) -> str:
    """Return a trimmed string representation for ``value`` suitable for JSON."""

    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_header(value: Any) -> str:
    """Return a normalised lowercase header representation."""

    return " ".join(_stringify(value).lower().split())


def _row_is_empty(row: Iterable[Any]) -> bool:
    """Return ``True`` when every cell in ``row`` is blank."""

    return all(not _stringify(cell) for cell in row)


def _load_excel_rows(document_bytes: bytes) -> List[List[Any]]:
    """Load spreadsheet rows using ``openpyxl`` with an ``xlrd`` fallback for XLS."""

    stream = BytesIO(document_bytes)
    try:
        workbook = load_workbook(stream, data_only=True, read_only=True)
    except Exception as openpyxl_error:  # pragma: no cover - exercised in XLS fallback
        if xlrd is None:
            raise ValueError("The provided Excel file could not be parsed.") from openpyxl_error
    else:
        worksheet = workbook.active
        return [list(row) for row in worksheet.iter_rows(values_only=True)]

    try:  # pragma: no cover - requires legacy XLS fixtures
        book = xlrd.open_workbook(file_contents=document_bytes)
    except Exception as xls_error:  # pragma: no cover - defensive fallback path
        raise ValueError("The provided Excel file could not be parsed.") from xls_error

    sheet = book.sheet_by_index(0)
    total_columns = getattr(sheet, "ncols", 0)
    if total_columns == 0:
        return [sheet.row_values(index) for index in range(sheet.nrows)]

    return [
        sheet.row_values(index, end_colx=total_columns)
        for index in range(sheet.nrows)
    ]


def _locate_header(rows: List[List[Any]]) -> tuple[int, Dict[str, int]]:
    """Return the header row index plus a mapping between logical and column indices."""

    for index, row in enumerate(rows):
        if _row_is_empty(row):
            continue
        normalised = [_normalize_header(cell) for cell in row]
        mapping: Dict[str, int] = {}
        for key, aliases in _HEADER_ALIASES.items():
            for col_index, cell in enumerate(normalised):
                if cell in aliases:
                    mapping[key] = col_index
                    break
        if len(mapping) == len(_HEADER_ALIASES):
            return index, mapping
    raise ValueError("The Excel sheet does not contain the expected scorer headers.")


def _extract_metadata(rows: Iterable[List[Any]]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Derive table metadata (title, competition, category, season) from ``rows``."""

    lines: List[str] = []
    for row in rows:
        text = " ".join(filter(None, (_stringify(cell) for cell in row))).strip()
        if text:
            lines.append(text)

    if not lines:
        return None, None, None, None

    title = lines[0]
    season_index = next((idx for idx, line in enumerate(lines) if "Temporada" in line), None)

    season: Optional[str] = None
    descriptor: Optional[str] = None
    if season_index is not None:
        season_line = lines[season_index]
        before, _, after = season_line.partition("Temporada")
        season = _stringify(after) or None
        descriptor = _stringify(before).strip(",") or None
        if not descriptor and season_index > 0:
            descriptor = lines[season_index - 1]
    else:
        descriptor = title

    competition: Optional[str] = None
    category: Optional[str] = None
    if descriptor:
        if "," in descriptor:
            first, _, rest = descriptor.partition(",")
            competition = first.strip() or None
            category = rest.strip() or None
        else:
            competition = descriptor.strip() or None

    return title or None, competition, category, season


def _parse_int_cell(value: Any) -> Optional[int]:
    """Return an integer extracted from ``value`` when possible."""

    text = _stringify(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text.replace(",", ".")))
        except ValueError:
            return None


def _parse_ratio_cell(value: Any) -> Optional[float]:
    """Return a float extracted from ``value`` when possible."""

    text = _stringify(value)
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _parse_goals_cell(value: Any) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Return total goals, penalty goals and the textual detail from ``value``."""

    text = _stringify(value)
    if not text:
        return None, None, None

    match = _PENALTIES_RE.search(text)
    penalties = int(match.group(1)) if match else None
    numbers = _NUMBER_RE.findall(text)
    total = int(numbers[0]) if numbers else None
    details = text if text else (str(total) if total is not None else None)
    return total, penalties, details


class TopScorersExcelParser(TopScorersParser):
    """Decode top scorers information from uploaded Excel spreadsheets."""

    def parse(self, document_bytes: bytes) -> TopScorersTable:
        """Parse ``document_bytes`` into a :class:`TopScorersTable` instance."""

        rows = _load_excel_rows(document_bytes)
        if not rows:
            raise ValueError("The Excel sheet does not contain any data.")

        header_index, mapping = _locate_header(rows)
        title, competition, category, season = _extract_metadata(rows[:header_index])

        scorers: List[TopScorerEntry] = []
        for raw_row in rows[header_index + 1 :]:
            if _row_is_empty(raw_row):
                continue

            player = _stringify(raw_row[mapping["player"]])
            if not player:
                continue

            team = _stringify(raw_row[mapping["team"]]) or None
            group = _stringify(raw_row[mapping["group"]]) or None
            matches = _parse_int_cell(raw_row[mapping["matches"]])
            goals_total, penalty_goals, goals_details = _parse_goals_cell(
                raw_row[mapping["goals"]]
            )
            ratio = _parse_ratio_cell(raw_row[mapping["ratio"]])
            if ratio is None and matches and goals_total is not None and matches != 0:
                ratio = goals_total / matches

            raw_lines = [
                value
                for value in (
                    _stringify(raw_row[mapping["player"]]),
                    _stringify(raw_row[mapping["team"]]),
                    _stringify(raw_row[mapping["group"]]),
                    _stringify(raw_row[mapping["matches"]]),
                    _stringify(raw_row[mapping["goals"]]),
                    _stringify(raw_row[mapping["ratio"]]),
                )
                if value
            ]

            scorers.append(
                TopScorerEntry(
                    player=player,
                    team=team,
                    group=group or category,
                    matches_played=matches,
                    goals_total=goals_total,
                    goals_details=goals_details,
                    penalty_goals=penalty_goals,
                    goals_per_match=ratio,
                    raw_lines=raw_lines,
                )
            )

        if not scorers:
            raise ValueError("No scorer entries were found in the provided Excel file.")

        indexed = list(enumerate(scorers))
        indexed.sort(key=lambda item: (-(item[1].goals_total or -1), item[0]))
        ordered = [entry for _, entry in indexed]

        return TopScorersTable(
            title=title,
            competition=competition,
            category=category,
            season=season,
            scorers=ordered,
        )
