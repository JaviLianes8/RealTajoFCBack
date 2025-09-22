"""Domain services for extracting structured classification data from PDFs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from app.domain.models.document import ParsedDocument


_STAT_KEYS: List[str] = [
    "points",
    "played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "last_points",
    "sanction_points",
]

_ROW_INDEX_PATTERN = re.compile(r"^\d+")
_ROW_HAS_LETTER_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_ROW_PATTERN = re.compile(r"^(?P<position>\d+)\s*(?P<body>.+)$")
_TRAILING_NUMBERS_PATTERN = re.compile(r"(\d[\d\s]*)$")


@dataclass(frozen=True)
class ClassificationRow:
    """Represents a single team entry within the classification table."""

    position: int
    team: str
    stats: dict[str, int | None] = field(default_factory=dict)
    raw: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the classification row."""

        return {
            "position": self.position,
            "team": self.team,
            "stats": {key: value for key, value in self.stats.items()},
            "raw": self.raw,
        }


@dataclass(frozen=True)
class ClassificationTable:
    """Represents the extracted classification section of a PDF document."""

    headers: List[str] = field(default_factory=list)
    rows: List[ClassificationRow] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation of the classification table."""

        return {
            "headers": list(self.headers),
            "rows": [row.to_dict() for row in self.rows],
        }


def extract_classification(document: ParsedDocument) -> ClassificationTable:
    """Extract the classification table from the parsed document content."""

    lines: List[str] = [line for page in document.pages for line in page.content]
    normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]

    start_index = _find_section_start(normalized_lines)
    end_index = _find_section_end(normalized_lines, start_index)

    section_lines = normalized_lines[start_index:end_index]
    if not section_lines:
        return ClassificationTable()

    headers = section_lines[:2] if len(section_lines) >= 2 else section_lines
    row_lines = _merge_row_lines(section_lines[len(headers) :])

    rows: List[ClassificationRow] = []
    for line in row_lines:
        parsed_row = _parse_row(line)
        if parsed_row is not None:
            rows.append(parsed_row)

    return ClassificationTable(headers=headers, rows=rows)


def _find_section_start(lines: List[str]) -> int:
    """Return the index of the line that marks the classification header."""

    for index, line in enumerate(lines):
        if "equipos" in line.casefold():
            return index
    raise ValueError("The classification header line was not found in the document.")


def _find_section_end(lines: List[str], start_index: int) -> int:
    """Return the index of the line where the classification section ends."""

    for index in range(start_index, len(lines)):
        lowered_line = lines[index].casefold()
        if "resultado provisional" in lowered_line or lowered_line.startswith("(*)"):
            return index
    return len(lines)


def _parse_row(line: str) -> ClassificationRow | None:
    """Parse a row of the classification table into a structured entry."""

    match = _ROW_PATTERN.match(line)
    if match is None:
        return None

    position = int(match.group("position"))
    body = match.group("body").strip()
    if not body:
        return None

    stats_section_match = _TRAILING_NUMBERS_PATTERN.search(body)
    if stats_section_match is None:
        team = body
        stats_section = ""
    else:
        stats_section = stats_section_match.group(1)
        team = body[: stats_section_match.start()].strip()

    if not team:
        return None

    stats_values = [int(token) for token in re.findall(r"\d+", stats_section)]
    stats = {
        key: stats_values[index] if index < len(stats_values) else None
        for index, key in enumerate(_STAT_KEYS)
    }

    return ClassificationRow(position=position, team=team, stats=stats, raw=line)


def _merge_row_lines(lines: List[str]) -> List[str]:
    """Merge row fragments that span multiple lines into single entries."""

    merged_rows: List[str] = []
    current_row: str | None = None

    for line in lines:
        if _is_row_start(line):
            if current_row:
                merged_rows.append(current_row.strip())
            current_row = line
        elif current_row:
            current_row = f"{current_row} {line}".strip()

    if current_row:
        merged_rows.append(current_row.strip())

    return merged_rows


def _is_row_start(line: str) -> bool:
    """Return ``True`` when the provided line starts a new classification row."""

    return bool(_ROW_INDEX_PATTERN.match(line) and _ROW_HAS_LETTER_PATTERN.search(line))
