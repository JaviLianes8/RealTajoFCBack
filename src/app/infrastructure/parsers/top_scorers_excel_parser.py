"""Excel parser for extracting top scorers tables."""
from __future__ import annotations

import re
from importlib import import_module
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, List, Optional

from openpyxl import load_workbook

def _parse_version_tuple(raw_version: str) -> tuple[int, ...]:
    """Return a tuple with the numeric portions of ``raw_version``."""

    parts = re.findall(r"\d+", raw_version)
    return tuple(int(part) for part in parts)


def _build_xls_loaders() -> List[Callable[[bytes], List[List[Any]]]]:
    """Return XLS loader callables using the available optional dependencies."""

    loaders: List[Callable[[bytes], List[List[Any]]]] = []

    for module_name in ("xlrd", "xlrd3"):
        try:  # pragma: no cover - depends on optional runtime dependencies
            module = import_module(module_name)
        except Exception:  # pragma: no cover - module not installed or unusable
            continue

        version = _parse_version_tuple(getattr(module, "__version__", ""))
        if module_name == "xlrd" and version >= (2, 0, 0):
            # xlrd >= 2 removed support for legacy XLS files, fall back to xlrd3.
            continue

        open_workbook = getattr(module, "open_workbook", None)
        if not callable(open_workbook):
            continue

        def _load_with_xlrd(
            document_bytes: bytes, *, _module: Any = module
        ) -> List[List[Any]]:
            book = _module.open_workbook(file_contents=document_bytes)
            sheet = book.sheet_by_index(0)
            total_columns = getattr(sheet, "ncols", 0)
            rows: List[List[Any]] = []
            for index in range(sheet.nrows):
                if total_columns:
                    values = list(sheet.row_values(index, end_colx=total_columns))
                    if len(values) < total_columns:
                        values.extend([""] * (total_columns - len(values)))
                else:
                    values = list(sheet.row_values(index))
                rows.append(values)
            return rows

        loaders.append(_load_with_xlrd)

    try:  # pragma: no cover - depends on optional runtime dependencies
        pyexcel_module = import_module("pyexcel_xls")
    except Exception:  # pragma: no cover - module not installed or unusable
        pyexcel_module = None

    if pyexcel_module is not None:
        get_data = getattr(pyexcel_module, "get_data", None)
        if callable(get_data):

            def _load_with_pyexcel(document_bytes: bytes) -> List[List[Any]]:
                data = get_data(BytesIO(document_bytes), file_type="xls")
                if not data:
                    return []
                first_sheet = next(iter(data.values()), [])
                max_length = max((len(row) for row in first_sheet), default=0)
                normalised_rows: List[List[Any]] = []
                for row in first_sheet:
                    values = list(row)
                    if max_length and len(values) < max_length:
                        values.extend([""] * (max_length - len(values)))
                    normalised_rows.append(values)
                return normalised_rows

            loaders.append(_load_with_pyexcel)

    return loaders


_XLS_LOADERS = _build_xls_loaders()

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
    """Load spreadsheet rows using ``openpyxl`` with optional XLS fallbacks."""

    stream = BytesIO(document_bytes)
    try:
        workbook = load_workbook(stream, data_only=True, read_only=True)
    except Exception as openpyxl_error:  # pragma: no cover - exercised in XLS fallback
        errors: List[Exception] = []
        for loader in _XLS_LOADERS:
            try:
                return loader(document_bytes)
            except Exception as loader_error:  # pragma: no cover - defensive fallback path
                errors.append(loader_error)
        root_error = errors[-1] if errors else openpyxl_error
        raise ValueError("The provided Excel file could not be parsed.") from root_error
    else:
        worksheet = workbook.active
        return [list(row) for row in worksheet.iter_rows(values_only=True)]


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
