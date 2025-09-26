"""Domain services for extracting structured classification data from PDFs."""
from __future__ import annotations

import re
from datetime import datetime, date
from typing import List, Optional, Sequence

from app.domain.models.classification import (
    ClassificationLastMatch,
    ClassificationLastMatchTeam,
    ClassificationTable,
)
from app.domain.models.document import ParsedDocument
from app.domain.services.classification_decoders import (
    ClassificationRowDecoder,
    RowAssembler,
    StatisticsDecoder,
    StatisticsDecoderConfig,
)


_STAT_KEYS: Sequence[str] = (
    "points",
    "played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "last_points",
    "sanction_points",
)


_STAT_LENGTH_RULES: Sequence[tuple[int, ...]] = (
    (3, 2, 1),  # points can reach triple digits with long seasons
    (2, 1),  # played
    (2, 1),  # wins
    (2, 1),  # draws
    (2, 1),  # losses
    (2, 1),  # goals for
    (2, 1),  # goals against
    (2, 1),  # recent form points
    (2, 1),  # sanction points
)


class ClassificationExtractorService:
    """Coordinate the extraction of classification data from parsed documents."""

    def __init__(
        self,
        row_decoder: ClassificationRowDecoder | None = None,
        row_assembler: RowAssembler | None = None,
    ) -> None:
        """Configure the extractor with optional custom collaborators."""

        if row_decoder is None:
            statistics_decoder = StatisticsDecoder(
                StatisticsDecoderConfig(stat_keys=_STAT_KEYS, length_rules=_STAT_LENGTH_RULES)
            )
            self._row_decoder = ClassificationRowDecoder(_STAT_KEYS, statistics_decoder)
        else:
            self._row_decoder = row_decoder
        self._row_assembler = row_assembler or RowAssembler()

    def extract(self, document: ParsedDocument) -> ClassificationTable:
        """Return the classification table contained in ``document``."""

        lines: List[str] = [line for page in document.pages for line in page.content]
        normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]

        start_index = self._find_section_start(normalized_lines)
        last_match = self._extract_last_match(normalized_lines, start_index)
        end_index = self._find_section_end(normalized_lines, start_index)

        section_lines = normalized_lines[start_index:end_index]
        if not section_lines:
            return ClassificationTable()

        headers = section_lines[:2] if len(section_lines) >= 2 else section_lines
        row_lines = self._row_assembler.merge(section_lines[len(headers) :])

        rows = [
            parsed_row
            for line in row_lines
            if (parsed_row := self._row_decoder.decode(line)) is not None
        ]

        return ClassificationTable(headers=headers, rows=rows, last_match=last_match)

    @staticmethod
    def _find_section_start(lines: Sequence[str]) -> int:
        """Return the index of the line that marks the classification header."""

        for index, line in enumerate(lines):
            if "equipos" in line.casefold():
                return index
        raise ValueError("The classification header line was not found in the document.")

    @staticmethod
    def _find_section_end(lines: Sequence[str], start_index: int) -> int:
        """Return the index of the line where the classification section ends."""

        for index in range(start_index, len(lines)):
            lowered_line = lines[index].casefold()
            if "resultado provisional" in lowered_line or lowered_line.startswith("(*)"):
                return index
        return len(lines)

    @staticmethod
    def _extract_last_match(
        lines: Sequence[str], start_index: int
    ) -> ClassificationLastMatch | None:
        """Extract the Real Tajo fixture summary located before the classification table."""

        preamble = list(lines[:start_index])
        if not preamble:
            return None

        match_line = _locate_real_tajo_line(preamble)
        if match_line is None:
            return None

        home_segment, away_segment = _split_match_line(match_line)
        if home_segment is None or away_segment is None:
            home_segment, away_segment = _split_line_without_separator(match_line)
        if home_segment is None or away_segment is None:
            return None

        home_team = _parse_team_segment(home_segment, fallback_name="REAL TAJO")
        away_team = _parse_team_segment(away_segment)

        matchday, match_date = _parse_match_header(preamble)

        return ClassificationLastMatch(
            matchday=matchday,
            date=match_date,
            home_team=home_team,
            away_team=away_team,
        )


def extract_classification(document: ParsedDocument) -> ClassificationTable:
    """Convenience wrapper that extracts the classification table from ``document``."""

    extractor = ClassificationExtractorService()
    return extractor.extract(document)


__all__ = [
    "ClassificationExtractorService",
    "extract_classification",
]


def _locate_real_tajo_line(lines: Sequence[str]) -> Optional[str]:
    """Return the line describing the Real Tajo fixture if present."""

    for index, line in enumerate(lines):
        if "REAL TAJO" not in line.upper():
            continue

        accumulated = line.strip()
        if _contains_match_separator(accumulated):
            return accumulated

        # Attempt to merge up to two subsequent lines to recover split fixtures.
        lookahead_index = index + 1
        while lookahead_index < len(lines) and lookahead_index <= index + 2:
            next_line = lines[lookahead_index].strip()
            if not next_line:
                lookahead_index += 1
                continue
            accumulated = f"{accumulated} {next_line}".strip()
            if _contains_match_separator(next_line) or _contains_match_separator(accumulated):
                return accumulated
            lookahead_index += 1

        return accumulated
    return None


def _contains_match_separator(text: str) -> bool:
    """Return ``True`` when ``text`` contains an explicit match separator."""

    return " - " in text or re.search(r"\s-\s", text) is not None


def _split_match_line(line: str) -> tuple[Optional[str], Optional[str]]:
    """Split a match line into home and away segments."""

    separator_match = re.search(r"\s-\s", line)
    if separator_match:
        start, end = separator_match.span()
        home_segment = line[:start].strip()
        away_segment = line[end:].strip()
        return home_segment or None, away_segment or None

    if " - " in line:
        home_segment, away_segment = line.split(" - ", 1)
        return home_segment.strip() or None, away_segment.strip() or None

    return None, None


def _split_line_without_separator(line: str) -> tuple[Optional[str], Optional[str]]:
    """Split a match line lacking explicit separators using score heuristics."""

    pattern = re.compile(
        r"(REAL TAJO(?:\s+[A-ZÁÉÍÓÚÜÑ.]+)*)\s+(\d+)\s+(\d+)\s+([A-ZÁÉÍÓÚÜÑ0-9 .'-]+)",
        re.IGNORECASE,
    )
    match = pattern.search(line)
    if match is None:
        return None, None

    home_name = match.group(1).strip()
    home_score = match.group(2)
    away_score = match.group(3)
    away_name = match.group(4).strip()

    home_segment = f"{home_name} {home_score}".strip()
    away_segment = f"{away_score} {away_name}".strip()

    return home_segment or None, away_segment or None


def _parse_team_segment(segment: str, fallback_name: str | None = None) -> ClassificationLastMatchTeam:
    """Decode a team segment extracting its name and score."""

    cleaned = segment.strip()
    if not cleaned:
        name = fallback_name or ""
        return ClassificationLastMatchTeam(name=name, score=0)

    trailing_score = re.search(r"(\d+)\s*$", cleaned)
    leading_score = re.match(r"^(\d+)\s+", cleaned)

    if trailing_score:
        score = int(trailing_score.group(1))
        name = cleaned[: trailing_score.start()].strip()
    elif leading_score:
        score = int(leading_score.group(1))
        name = cleaned[leading_score.end() :].strip()
    else:
        score = 0
        name = cleaned

    if not name and fallback_name:
        name = fallback_name

    return ClassificationLastMatchTeam(name=name, score=score)


def _parse_match_header(lines: Sequence[str]) -> tuple[Optional[int], Optional[date]]:
    """Retrieve matchday number and date from the header preceding the fixture list."""

    jornada_pattern = re.compile(
        r"Jornada\s+(\d+)\s*\((\d{2}-\d{2}-\d{4})\)", re.IGNORECASE
    )

    for line in reversed(lines):
        match = jornada_pattern.search(line)
        if match is None:
            continue

        matchday = int(match.group(1))
        raw_date = match.group(2)
        try:
            parsed_date = datetime.strptime(raw_date, "%d-%m-%Y").date()
        except ValueError:
            parsed_date = None
        return matchday, parsed_date

    return None, None
