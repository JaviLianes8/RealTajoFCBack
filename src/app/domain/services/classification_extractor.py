"""Domain services for extracting structured classification data from PDFs."""
from __future__ import annotations

import re
from typing import List, Sequence

from app.domain.models.classification import ClassificationTable
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

        return ClassificationTable(headers=headers, rows=rows)

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


def extract_classification(document: ParsedDocument) -> ClassificationTable:
    """Convenience wrapper that extracts the classification table from ``document``."""

    extractor = ClassificationExtractorService()
    return extractor.extract(document)


__all__ = [
    "ClassificationExtractorService",
    "extract_classification",
]
