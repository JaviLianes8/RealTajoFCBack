"""PDF parser extracting matchday results into structured data."""
from __future__ import annotations

import re
from typing import List, Sequence

from app.application.process_document import DocumentParser
from app.application.process_matchday_results import MatchdayParser
from app.domain.models.document import ParsedDocument
from app.domain.models.matchday_results import MatchResult, MatchdayResults
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser


class MatchdayPdfParser(MatchdayParser):
    """Parse competition matchday results from PDF bytes."""

    _INLINE_RESULT_PATTERN = re.compile(
        r"(?P<home>[A-Z0-9 .\-/&']+?)\s+"
        r"(?P<home_score>\d+)\s*-\s*(?P<away_score>\d+)\s+"
        r"(?:\d{2}-\d{2}-\d{4}\s+)?(?:\d{1,2}:\d{2}\s+)?"
        r"(?P<away>[A-Z0-9 .\-/&']+)",
    )
    _SCORE_ONLY_PATTERN = re.compile(r"^(?P<home_score>\d+)\s*-\s*(?P<away_score>\d+)$")
    _MATCHDAY_PATTERN = re.compile(r"Jornada\s*(?P<number>\d+)", re.IGNORECASE)
    _SEASON_PATTERN = re.compile(r"Temporada\s+(?P<season>[\w/-]+)", re.IGNORECASE)

    def __init__(self, pdf_parser: DocumentParser | None = None) -> None:
        """Initialize the parser with a lower level PDF text extractor."""

        self._pdf_parser = pdf_parser or PdfDocumentParser()

    def parse(self, document_bytes: bytes) -> MatchdayResults:
        """Parse ``document_bytes`` into a ``MatchdayResults`` aggregate."""

        parsed_document = self._pdf_parser.parse(document_bytes)
        lines = _flatten_document(parsed_document)
        matchday_number = self._extract_matchday_number(lines)
        competition, season = self._extract_competition_metadata(lines)
        matches = self._extract_matches(lines)
        return MatchdayResults(
            competition=competition,
            season=season,
            matchday=matchday_number,
            matches=matches,
        )

    def _extract_matchday_number(self, lines: Sequence[str]) -> int:
        """Return the matchday number found within ``lines``."""

        for line in lines:
            match = self._MATCHDAY_PATTERN.search(line)
            if match:
                return int(match.group("number"))
        raise ValueError("The PDF does not specify a matchday number.")

    def _extract_competition_metadata(self, lines: Sequence[str]) -> tuple[str | None, str | None]:
        """Return competition title and season extracted from the header lines."""

        competition = None
        season = None
        for line in lines:
            if "Temporada" in line:
                competition = line.split("Temporada")[0].strip() or None
                season_match = self._SEASON_PATTERN.search(line)
                if season_match:
                    season = season_match.group("season")
                continue
            if competition is None and line:
                competition = line.strip()
        return competition, season

    def _extract_matches(self, lines: Sequence[str]) -> List[MatchResult]:
        """Parse the scoreboard entries contained in ``lines``."""

        text_blob = "\n".join(lines)
        matches = self._parse_inline_results(text_blob)
        if matches:
            return matches
        return self._parse_separated_results(lines)

    def _parse_inline_results(self, text_blob: str) -> List[MatchResult]:
        """Extract matches where teams and scores appear on the same textual block."""

        results: List[MatchResult] = []
        for match in self._INLINE_RESULT_PATTERN.finditer(text_blob):
            home_team = match.group("home").strip()
            away_team = match.group("away").strip()
            results.append(
                MatchResult(
                    home_team=_normalize_team_name(home_team),
                    away_team=_normalize_team_name(away_team),
                    home_score=int(match.group("home_score")),
                    away_score=int(match.group("away_score")),
                )
            )
        return results

    def _parse_separated_results(self, lines: Sequence[str]) -> List[MatchResult]:
        """Extract matches expressed with the score on a separate line."""

        results: List[MatchResult] = []
        for index, line in enumerate(lines):
            score_match = self._SCORE_ONLY_PATTERN.match(line)
            if not score_match:
                continue
            home_team = _find_previous_team(lines, index)
            away_team = _find_next_team(lines, index)
            if not home_team or not away_team:
                continue
            results.append(
                MatchResult(
                    home_team=home_team,
                    away_team=away_team,
                    home_score=int(score_match.group("home_score")),
                    away_score=int(score_match.group("away_score")),
                )
            )
        return results


def _flatten_document(document: ParsedDocument) -> List[str]:
    """Return a flat list with all non-empty lines in ``document``."""

    lines: List[str] = []
    for page in document.pages:
        lines.extend(filter(None, (line.strip() for line in page.content)))
    return lines


def _normalize_team_name(raw_name: str) -> str:
    """Return a cleaned team name stripping duplicated whitespace."""

    return re.sub(r"\s+", " ", raw_name).strip()


def _find_previous_team(lines: Sequence[str], index: int) -> str | None:
    """Return the closest meaningful line above ``index`` representing a team."""

    for cursor in range(index - 1, -1, -1):
        candidate = lines[cursor].strip()
        if not candidate or _is_metadata_line(candidate):
            continue
        return _normalize_team_name(candidate)
    return None


def _find_next_team(lines: Sequence[str], index: int) -> str | None:
    """Return the closest meaningful line below ``index`` representing a team."""

    for cursor in range(index + 1, len(lines)):
        candidate = lines[cursor].strip()
        if not candidate or _is_metadata_line(candidate):
            continue
        return _normalize_team_name(candidate)
    return None


def _is_metadata_line(line: str) -> bool:
    """Determine whether ``line`` represents metadata rather than a team name."""

    if not line:
        return True
    if line.startswith("Campo:"):
        return True
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", line):
        return True
    if re.fullmatch(r"\d{1,2}:\d{2}", line):
        return True
    if line.lower().startswith("descansa"):
        return True
    return False
