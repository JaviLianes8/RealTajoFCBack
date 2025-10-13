"""Supporting components for decoding classification table rows."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from app.domain.models.classification import ClassificationRow


_ROW_INDEX_PATTERN = re.compile(r"^\d+")
_ROW_HAS_LETTER_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_ROW_PATTERN = re.compile(r"^(?P<position>\d+)\s*(?P<body>.+)$")
_TRAILING_STATS_PATTERN = re.compile(r"([\d\sGEP]+)$", re.IGNORECASE)
_FORM_TOKEN_TO_POINTS = {"G": "3", "E": "1", "P": "0"}


@dataclass(frozen=True)
class StatisticsDecoderConfig:
    """Configuration values governing statistics decoding."""

    stat_keys: Sequence[str]
    length_rules: Sequence[tuple[int, ...]]


class StatisticsDecoder:
    """Decode trailing numeric sections into structured statistics."""

    def __init__(self, config: StatisticsDecoderConfig) -> None:
        """Initialize the decoder with its configuration."""

        self._stat_keys = list(config.stat_keys)
        self._length_rules = list(config.length_rules)

    def decode(self, stats_section: str) -> List[int]:
        """Return statistics extracted from the provided section."""

        expected_values = len(self._stat_keys)
        tokens = re.findall(r"\d+", stats_section)

        values = self._decode_from_tokens(tokens, expected_values)
        if values is None:
            values = self._normalize_values([], expected_values, stats_section)

        return self._pad_missing_values(values, expected_values)

    def _decode_from_tokens(
        self, tokens: Iterable[str], expected_values: int
    ) -> List[int] | None:
        token_list = list(tokens)
        if not token_list:
            return None

        numeric_tokens = [int(token) for token in token_list]

        if len(numeric_tokens) >= expected_values:
            candidate = numeric_tokens[:expected_values]
            if self._stats_are_consistent(candidate):
                return candidate

        digits_sequence = "".join(token_list)
        segmented_values = self._segment_digits_sequence(digits_sequence, expected_values)
        if segmented_values is not None:
            return segmented_values

        if len(numeric_tokens) >= expected_values:
            return numeric_tokens[:expected_values]

        values: List[int] = []
        for token in numeric_tokens:
            if len(values) >= expected_values:
                break
            values.append(token)

        if len(token_list) == 1 and len(digits_sequence := "".join(token_list)) > 2 and len(values) < expected_values:
            values = []
            return self._normalize_values(values, expected_values, digits_sequence)

        normalized = self._normalize_values(values, expected_values, digits_sequence)
        return normalized if normalized else None

    def _normalize_values(
        self, values: List[int], expected_values: int, stats_section: str
    ) -> List[int]:
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

    def _pad_missing_values(self, values: List[int], expected_values: int) -> List[int]:
        if len(values) >= expected_values:
            return values[:expected_values]

        padded_values = list(values)
        default_value = padded_values[-1] if padded_values else 0

        while len(padded_values) < expected_values:
            padded_values.append(default_value)

        return padded_values

    def _segment_digits_sequence(
        self, digits: str, expected_values: int
    ) -> List[int] | None:
        if not digits:
            return None

        values: List[int] = []
        solution: List[int] | None = None

        def backtrack(stat_index: int, position: int) -> bool:
            nonlocal solution

            if stat_index == expected_values:
                if position == len(digits) and self._stats_are_consistent(values):
                    solution = list(values)
                    return True
                return False

            remaining_digits = len(digits) - position
            remaining_stats = expected_values - stat_index
            if remaining_digits < remaining_stats:
                return False

            for length in self._length_rules[stat_index]:
                if position + length > len(digits):
                    continue

                value = int(digits[position : position + length])
                values.append(value)

                if self._partial_stats_are_valid(values):
                    if backtrack(stat_index + 1, position + length):
                        return True

                values.pop()

            return False

        backtrack(0, 0)
        return solution

    def _partial_stats_are_valid(self, values: Sequence[int]) -> bool:
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

    def _stats_are_consistent(self, values: Sequence[int]) -> bool:
        if len(values) < len(self._stat_keys):
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


class ClassificationRowDecoder:
    """Translate textual row representations into domain objects."""

    def __init__(
        self,
        stat_keys: Sequence[str],
        statistics_decoder: StatisticsDecoder,
    ) -> None:
        """Store dependencies required to decode a classification row."""

        self._stat_keys = list(stat_keys)
        self._statistics_decoder = statistics_decoder

    def decode(self, line: str) -> ClassificationRow | None:
        """Return the row encoded in ``line`` or ``None`` when parsing fails."""

        match = _ROW_PATTERN.match(line)
        if match is None:
            return None

        position = int(match.group("position"))
        body = match.group("body").strip()
        if not body:
            return None

        stats_section_match = _TRAILING_STATS_PATTERN.search(body)
        if stats_section_match is None:
            team = body
            stats_section = ""
        else:
            stats_section = _normalize_stats_section(stats_section_match.group(1))
            team = body[: stats_section_match.start()].strip()

        if not team:
            return None

        stats_values = self._statistics_decoder.decode(stats_section)
        stats = {
            key: stats_values[index] if index < len(stats_values) else None
            for index, key in enumerate(self._stat_keys)
        }

        return ClassificationRow(position=position, team=team, stats=stats, raw=line)


def _normalize_stats_section(section: str) -> str:
    """Return ``section`` replacing known form tokens with numeric values."""

    tokens = section.split()
    if not tokens:
        return section

    normalized_tokens: List[str] = []
    accumulated_form_points: List[int] = []

    def flush_form_points() -> None:
        if accumulated_form_points:
            normalized_tokens.append(str(sum(accumulated_form_points)))
            accumulated_form_points.clear()

    for token in tokens:
        mapped = _FORM_TOKEN_TO_POINTS.get(token.upper())
        if mapped is not None:
            accumulated_form_points.append(int(mapped))
            continue

        flush_form_points()
        normalized_tokens.append(token)

    flush_form_points()

    return " ".join(normalized_tokens)


class RowAssembler:
    """Compose complete rows from potentially fragmented line sequences."""

    def merge(self, lines: Sequence[str]) -> List[str]:
        """Return a list of assembled row strings."""

        merged_rows: List[str] = []
        current_row: str | None = None

        for line in lines:
            if self._is_row_start(line):
                if current_row:
                    merged_rows.append(current_row.strip())
                current_row = line
            elif current_row:
                current_row = f"{current_row} {line}".strip()

        if current_row:
            merged_rows.append(current_row.strip())

        return merged_rows

    @staticmethod
    def _is_row_start(line: str) -> bool:
        return bool(_ROW_INDEX_PATTERN.match(line) and _ROW_HAS_LETTER_PATTERN.search(line))


__all__ = [
    "ClassificationRowDecoder",
    "RowAssembler",
    "StatisticsDecoder",
    "StatisticsDecoderConfig",
]

