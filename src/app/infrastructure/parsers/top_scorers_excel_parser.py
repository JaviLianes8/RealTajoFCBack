"""Excel parser for extracting top scorers tables."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
from typing import Iterable, List, Optional, Sequence
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.application.process_top_scorers import TopScorersParser
from app.domain.models.top_scorers import TopScorerEntry, TopScorersTable


@dataclass(frozen=True)
class _ColumnIndexes:
    """Hold the indexes of the expected scorer columns."""

    player: int
    team: int
    group: int
    matches: int
    goals: int
    ratio: int


class TopScorersExcelParser(TopScorersParser):
    """Parse `.xlsx` spreadsheets into :class:`TopScorersTable` instances."""

    _HEADER_ALIASES = {
        "player": {"jugador"},
        "team": {"equipo"},
        "group": {"grupo"},
        "matches": {"partidos", "partidos jugados"},
        "goals": {"goles"},
        "ratio": {"goles partido", "goles/partido", "goles por partido"},
    }

    _PENALTY_RE = re.compile(r"(\d+)\s+de\s+penalti", re.IGNORECASE)
    _SEASON_RE = re.compile(r"temporada\s+([\w\-/]+)", re.IGNORECASE)

    def parse(self, document_bytes: bytes) -> TopScorersTable:
        """Return the structured scorers table contained in ``document_bytes``."""

        try:
            workbook = load_workbook(BytesIO(document_bytes), data_only=True)
        except (InvalidFileException, BadZipFile) as error:
            raise ValueError("The provided file is not a valid Excel workbook.") from error
        worksheet = workbook.active
        header_row_index, column_indexes, metadata_values = self._locate_header(worksheet.iter_rows(values_only=True))
        if column_indexes is None or header_row_index is None:
            raise ValueError("Unable to locate the scorer table header in the spreadsheet.")

        scorers = self._extract_scorers(worksheet.iter_rows(values_only=True), header_row_index, column_indexes)
        metadata_text = " ".join(metadata_values).strip()
        title = metadata_text or None
        season = self._extract_season(metadata_text)
        competition, category = self._extract_competition_and_category(metadata_text, season)

        return TopScorersTable(
            title=title,
            competition=competition,
            category=category,
            season=season,
            scorers=scorers,
        )

    def _locate_header(
        self,
        rows: Iterable[Sequence[object | None]],
    ) -> tuple[Optional[int], Optional[_ColumnIndexes], List[str]]:
        """Return the header row position, column indexes and metadata text."""

        metadata_values: List[str] = []
        header_row_index: Optional[int] = None
        column_indexes: Optional[_ColumnIndexes] = None

        for index, row in enumerate(rows, start=1):
            values = [self._cell_to_str(cell) for cell in row]
            meaningful = [value for value in values if value]
            if not meaningful:
                continue

            header_candidates = [self._normalize_header(value) for value in meaningful]
            if self._is_header_row(header_candidates):
                header_row_index = index
                column_indexes = self._build_column_indexes(values)
                break

            metadata_values.extend(meaningful)

        return header_row_index, column_indexes, metadata_values

    def _extract_scorers(
        self,
        rows: Iterable[Sequence[object | None]],
        header_row_index: int,
        indexes: _ColumnIndexes,
    ) -> List[TopScorerEntry]:
        """Iterate rows after the header and convert them into scorer entries."""

        scorers: List[TopScorerEntry] = []
        for current_index, row in enumerate(rows, start=1):
            if current_index <= header_row_index:
                continue

            values = [self._cell_to_str(cell) for cell in row]
            if not any(values):
                continue

            player = values[indexes.player]
            if not player:
                continue

            goals_text = values[indexes.goals]
            goals_total, goals_details, penalties = self._parse_goals(goals_text)

            scorer = TopScorerEntry(
                player=player,
                team=values[indexes.team] or None,
                group=values[indexes.group] or None,
                matches_played=self._parse_int(values[indexes.matches]),
                goals_total=goals_total,
                goals_details=goals_details,
                penalty_goals=penalties,
                goals_per_match=self._parse_float(values[indexes.ratio]),
                raw_lines=[value for value in values if value],
            )
            scorers.append(scorer)

        return scorers

    def _build_column_indexes(self, row_values: Sequence[str]) -> _ColumnIndexes:
        """Map known header aliases to their corresponding column indexes."""

        resolved: dict[str, int] = {}
        for position, value in enumerate(row_values):
            normalized = self._normalize_header(value)
            if not normalized:
                continue
            for key, aliases in self._HEADER_ALIASES.items():
                if normalized in aliases and key not in resolved:
                    resolved[key] = position

        missing = [key for key in self._HEADER_ALIASES if key not in resolved]
        if missing:
            raise ValueError(f"Missing expected header columns: {', '.join(missing)}")

        return _ColumnIndexes(
            player=resolved["player"],
            team=resolved["team"],
            group=resolved["group"],
            matches=resolved["matches"],
            goals=resolved["goals"],
            ratio=resolved["ratio"],
        )

    def _is_header_row(self, normalized_values: Sequence[str]) -> bool:
        """Return ``True`` when ``normalized_values`` contain the expected columns."""

        present = set(normalized_values)
        required = {alias for aliases in self._HEADER_ALIASES.values() for alias in aliases}
        return {"jugador", "equipo", "goles"}.issubset(present) and bool(present & required)

    def _parse_goals(self, text: str) -> tuple[Optional[int], Optional[str], Optional[int]]:
        """Return total goals, detail text and penalties from ``text``."""

        if not text:
            return None, None, None

        total_match = re.search(r"\d+", text)
        total = int(total_match.group(0)) if total_match else None

        details_match = re.search(r"\(([^)]*)\)", text)
        details = details_match.group(1).strip() if details_match else None

        penalties: Optional[int] = None
        if details:
            penalty_match = self._PENALTY_RE.search(details)
            if penalty_match:
                penalties = int(penalty_match.group(1))

        return total, details, penalties

    def _extract_season(self, metadata_text: str) -> Optional[str]:
        """Return the detected season string from ``metadata_text``."""

        if not metadata_text:
            return None
        match = self._SEASON_RE.search(metadata_text)
        if not match:
            return None
        return match.group(1).strip() or None

    def _extract_competition_and_category(
        self, metadata_text: str, season: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Derive competition and category values from the metadata block."""

        if not metadata_text:
            return None, None

        working_text = metadata_text
        if season:
            season_index = working_text.lower().find("temporada")
            if season_index != -1:
                working_text = working_text[:season_index].strip()

        if not working_text:
            return None, None

        if "," in working_text:
            competition_part, category_part = working_text.split(",", 1)
            competition = competition_part.strip() or None
            category = category_part.strip() or None
        else:
            competition = working_text.strip() or None
            category = None

        return competition, category

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse ``value`` as integer when possible."""

        if not value:
            return None
        try:
            return int(float(value.replace(",", ".")))
        except (ValueError, AttributeError):
            return None

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse ``value`` as float when possible."""

        if not value:
            return None
        try:
            return float(value.replace(",", "."))
        except (ValueError, AttributeError):
            return None

    def _cell_to_str(self, cell: object | None) -> str:
        """Return a trimmed string representation of ``cell``."""

        if cell is None:
            return ""
        if isinstance(cell, str):
            return cell.strip()
        return str(cell).strip()

    def _normalize_header(self, value: str) -> str:
        """Normalize header ``value`` for comparison purposes."""

        return re.sub(r"\s+", " ", value.strip().lower())


class TopScorersParserError(ValueError):
    """Backward compatible error alias for external callers."""


__all__ = ["TopScorersExcelParser", "TopScorersParserError"]
