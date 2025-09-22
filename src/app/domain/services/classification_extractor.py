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


_COLUMN_STRUCTURE: List[dict] = [
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
]

_ROW_INDEX_PATTERN = re.compile(r"^\d+")
_ROW_HAS_LETTER_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_ROW_PATTERN = re.compile(r"^(?P<position>\d+)\s*(?P<body>.+)$")
_TRAILING_NUMBERS_PATTERN = re.compile(r"(\d[\d\s]*)$")

_STAT_LENGTH_RULES: List[tuple[int, ...]] = [
    (3, 2, 1),  # points can reach triple digits with long seasons
    (2, 1),  # played
    (2, 1),  # wins
    (2, 1),  # draws
    (2, 1),  # losses
    (2, 1),  # goals for
    (2, 1),  # goals against
    (2, 1),  # recent form points
    (2, 1),  # sanction points
]


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
            "points": self.stats.get("points"),
            "matches": {
                "played": self.stats.get("played"),
                "wins": self.stats.get("wins"),
                "draws": self.stats.get("draws"),
                "losses": self.stats.get("losses"),
            },
            "goals": {
                "for": self.stats.get("goals_for"),
                "against": self.stats.get("goals_against"),
            },
            "recent_form": {"points": self.stats.get("last_points")},
            "sanction": {"points": self.stats.get("sanction_points")},
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
            "metadata": {
                "headers": list(self.headers),
                "columns": _COLUMN_STRUCTURE,
            },
            "teams": [row.to_dict() for row in self.rows],
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

    stats_values = _extract_stat_values(stats_section)
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


def _extract_stat_values(stats_section: str) -> List[int]:
    """Return numeric statistics extracted from the row tail section."""

    expected_values = len(_STAT_KEYS)
    tokens = re.findall(r"\d+", stats_section)

    values = _decode_stats_from_tokens(tokens, expected_values)
    if values is None:
        values = _normalize_stat_values([], expected_values, stats_section)

    return _pad_missing_statistics(values, expected_values)


def _decode_stats_from_tokens(tokens: List[str], expected_values: int) -> List[int] | None:
    """Return statistics resolved from digit tokens when possible."""

    if not tokens:
        return None

    numeric_tokens = [int(token) for token in tokens]
    if len(numeric_tokens) >= expected_values:
        candidate = numeric_tokens[:expected_values]
        if _stats_are_consistent(candidate):
            return candidate

    digits_sequence = "".join(tokens)
    segmented_values = _segment_digits_sequence(digits_sequence, expected_values)
    if segmented_values is not None:
        return segmented_values

    if len(numeric_tokens) >= expected_values:
        return numeric_tokens[:expected_values]

    values: List[int] = []
    for index, token in enumerate(tokens):
        if len(values) >= expected_values:
            break

        remaining_slots = expected_values - len(values)
        tokens_left = len(tokens) - index

        if _should_split_token(token, remaining_slots, tokens_left):
            for digit in token:
                values.append(int(digit))
                if len(values) >= expected_values:
                    break
        else:
            values.append(int(token))

    normalized = _normalize_stat_values(values, expected_values, digits_sequence)
    return normalized if normalized else None


def _should_split_token(token: str, remaining_slots: int, tokens_left: int) -> bool:
    """Return ``True`` when the token must be split to fill missing stats."""

    if remaining_slots <= tokens_left:
        return False
    if len(token) <= 2:
        return False
    if len(set(token)) == 1:
        return True
    return tokens_left == 1


def _normalize_stat_values(
    values: List[int], expected_values: int, stats_section: str
) -> List[int]:
    """Fill missing statistic slots with sensible defaults when data is partial."""

    if len(values) >= expected_values:
        return values[:expected_values]

    digits = re.findall(r"\d", stats_section)
    if not digits:
        default_value = values[-1] if values else 0
        while len(values) < expected_values:
            values.append(default_value)
        return values

    default_value = 0 if all(digit == "0" for digit in digits) else (values[-1] if values else 0)

    while len(values) < expected_values:
        values.append(default_value)

    return values


def _pad_missing_statistics(values: List[int], expected_values: int) -> List[int]:
    """Ensure the returned statistics list always covers the expected columns."""

    if len(values) >= expected_values:
        return values[:expected_values]

    padded_values = list(values)
    default_value = padded_values[-1] if padded_values else 0

    while len(padded_values) < expected_values:
        padded_values.append(default_value)

    return padded_values


def _segment_digits_sequence(digits: str, expected_values: int) -> List[int] | None:
    """Return statistics obtained by segmenting a raw digit sequence."""

    if not digits:
        return None

    values: List[int] = []
    solution: List[int] | None = None

    def backtrack(stat_index: int, position: int) -> bool:
        nonlocal solution

        if stat_index == expected_values:
            if position == len(digits) and _stats_are_consistent(values):
                solution = list(values)
                return True
            return False

        remaining_digits = len(digits) - position
        remaining_stats = expected_values - stat_index
        if remaining_digits < remaining_stats:
            return False

        for length in _STAT_LENGTH_RULES[stat_index]:
            if position + length > len(digits):
                continue

            value = int(digits[position : position + length])
            values.append(value)

            if _partial_stats_are_valid(values):
                if backtrack(stat_index + 1, position + length):
                    return True

            values.pop()

        return False

    backtrack(0, 0)
    return solution


def _partial_stats_are_valid(values: List[int]) -> bool:
    """Return ``True`` while the partial segmentation remains coherent."""

    if len(values) <= 1:
        return True

    played = values[1]
    if len(values) >= 3 and values[2] > played:
        return False
    if len(values) >= 4 and values[2] + values[3] > played:
        return False
    if len(values) >= 5 and values[2] + values[3] + values[4] > played:
        return False

    return True


def _stats_are_consistent(values: List[int]) -> bool:
    """Return ``True`` when the provided statistics satisfy basic invariants."""

    if len(values) < len(_STAT_KEYS):
        return False

    points, played, wins, draws, losses, *_rest, last_points, sanction = values

    if played != wins + draws + losses:
        return False

    computed_points = wins * 3 + draws - sanction
    if computed_points < 0:
        return False

    if computed_points != points:
        return False

    if last_points < 0 or sanction < 0:
        return False

    return True
