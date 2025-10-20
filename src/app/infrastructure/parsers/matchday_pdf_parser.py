"""PDF parser capable of extracting matchday fixtures and results."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List

from app.application.process_document import DocumentParser
from app.application.process_matchday import MatchdayParser
from app.domain.models.document import ParsedDocument
from app.domain.models.matchday import Matchday, MatchFixture
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser


_INLINE_RESULT_RE = re.compile(
    r"^(?P<home>.+?)\s+(?P<home_score>\d+)\s*-\s*(?P<away_score>\d+)\s+(?P<away>.+?)$",
    re.IGNORECASE,
)
_SCORE_ONLY_RE = re.compile(r"^(?P<home>\d+)\s*-\s*(?P<away>\d+)$")
_TEAM_WITH_TRAILING_SCORE_RE = re.compile(
    r"^(?P<team>.+?)\s+(?P<home_score>\d+)\s*-\s*(?P<away_score>\d+)$"
)
_DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
_HEADER_PREFIXES = (
    "liga",
    "temporada",
    "calendario",
    "resultados",
    "equipos",
    "clasificacion",
    "clasificación",
)
_METADATA_PREFIXES = (
    "campo",
    "delegacion",
    "delegación",
    "r.f.f.m",
    "rffm",
    "federacion",
    "federación",
)


class MatchdayPdfParser(MatchdayParser):
    """Parse matchday PDFs into ``Matchday`` aggregates."""

    def __init__(self, document_parser: DocumentParser | None = None) -> None:
        """Initialize the parser with the optional low-level document parser."""

        self._document_parser = document_parser or PdfDocumentParser()

    def parse(self, document_bytes: bytes) -> Matchday:
        """Parse the provided PDF bytes into a ``Matchday`` domain model."""

        parsed_document = self._document_parser.parse(document_bytes)
        lines = self._flatten_lines(parsed_document)
        matchday_number = self._extract_matchday_number(lines)
        fixtures = self._extract_fixtures(lines)
        if not fixtures:
            raise ValueError("No fixtures were found in the provided matchday document.")
        return Matchday(number=matchday_number, fixtures=fixtures)

    def _flatten_lines(self, document: ParsedDocument) -> List[str]:
        """Return a flat list of non-empty lines from the parsed document."""

        lines: List[str] = []
        for page in document.pages:
            for line in page.content:
                cleaned = line.strip()
                if cleaned:
                    lines.append(cleaned)
        return lines

    def _extract_matchday_number(self, lines: List[str]) -> int:
        """Return the matchday number detected within the document lines."""

        for line in lines:
            match = re.search(r"jornada\s+(\d+)", line, re.IGNORECASE)
            if match:
                return int(match.group(1))
        raise ValueError("The matchday number could not be determined from the document.")

    def _extract_fixtures(self, lines: List[str]) -> List[MatchFixture]:
        """Return the list of fixtures extracted from the document lines."""

        fixtures: List[MatchFixture] = []
        team_buffer: List[str] = []
        pending_home: str | None = None
        pending_away: str | None = None
        pending_scores: tuple[int, int] | None = None
        pending_date: str | None = None
        pending_time: str | None = None
        awaiting_away: bool = False

        def finalize_fixture() -> None:
            nonlocal pending_home, pending_away, pending_scores, pending_date, pending_time, awaiting_away
            if pending_home is None or pending_away is None:
                return
            fixtures.append(
                MatchFixture(
                    home_team=pending_home,
                    away_team=pending_away,
                    home_score=pending_scores[0] if pending_scores else None,
                    away_score=pending_scores[1] if pending_scores else None,
                    is_bye=False,
                    date=pending_date,
                    time=pending_time,
                )
            )
            pending_home = None
            pending_away = None
            pending_scores = None
            pending_date = None
            pending_time = None
            awaiting_away = False

        def consume_team_buffer(on_score_line: bool = False) -> None:
            nonlocal pending_home, pending_away, pending_scores, pending_date, pending_time, awaiting_away
            if not team_buffer:
                return
            fragments = list(team_buffer)
            team_buffer.clear()
            joined = " ".join(fragments).lower()
            if "descansa" in joined:
                team_name = self._normalise_team_name(fragments)
                if team_name:
                    fixtures.append(
                        MatchFixture(
                            home_team=team_name,
                            away_team=None,
                            home_score=None,
                            away_score=None,
                            is_bye=True,
                        )
                    )
                pending_home = None
                pending_away = None
                pending_scores = None
                pending_date = None
                pending_time = None
                awaiting_away = False
                return
            if on_score_line and pending_home is None and len(fragments) >= 2:
                home_name = self._normalise_team_name(fragments[:-1])
                away_name = self._normalise_team_name([fragments[-1]])
                if home_name:
                    pending_home = home_name
                if away_name:
                    pending_away = away_name
                    awaiting_away = False
                else:
                    awaiting_away = True
                return
            name = self._normalise_team_name(fragments)
            if not name:
                return
            if pending_home is None:
                pending_home = name
                awaiting_away = awaiting_away or on_score_line
            elif pending_away is None or awaiting_away:
                pending_away = name
                awaiting_away = False
            else:
                finalize_fixture()
                pending_home = name
                pending_away = None
                pending_scores = None
                pending_date = None
                pending_time = None
                awaiting_away = on_score_line

        for raw_line in lines:
            line = self._normalise_whitespace(raw_line)
            if not line:
                continue

            lower_line = line.lower()
            if lower_line.startswith("jornada"):
                continue
            if any(lower_line.startswith(prefix) for prefix in _HEADER_PREFIXES):
                continue

            date_match = _DATE_RE.search(line)
            if date_match:
                pending_date = self._normalise_date(date_match.group(0))
            time_match = _TIME_RE.search(line)
            if time_match:
                pending_time = time_match.group(0)

            inline_match = _INLINE_RESULT_RE.match(line)
            if inline_match:
                consume_team_buffer()
                finalize_fixture()
                home_team = self._normalise_team_name([inline_match.group("home")])
                away_team = self._normalise_team_name([inline_match.group("away")])
                fixtures.append(
                    MatchFixture(
                        home_team=home_team,
                        away_team=away_team,
                        home_score=int(inline_match.group("home_score")),
                        away_score=int(inline_match.group("away_score")),
                        is_bye=False,
                        date=pending_date,
                        time=pending_time,
                    )
                )
                pending_home = None
                pending_away = None
                pending_scores = None
                pending_date = None
                pending_time = None
                continue

            trailing_score_match = _TEAM_WITH_TRAILING_SCORE_RE.match(line)
            if trailing_score_match:
                consume_team_buffer()
                team_name = self._normalise_team_name([
                    trailing_score_match.group("team")
                ])
                if team_name:
                    if pending_home is None:
                        pending_home = team_name
                    elif pending_away is None:
                        pending_away = team_name
                    else:
                        finalize_fixture()
                        pending_home = team_name
                        pending_away = None
                    pending_scores = (
                        int(trailing_score_match.group("home_score")),
                        int(trailing_score_match.group("away_score")),
                    )
                    awaiting_away = False
                continue

            if "descansa" in lower_line:
                team_buffer.append(line)
                consume_team_buffer()
                continue

            score_match = _SCORE_ONLY_RE.match(line)
            if score_match:
                consume_team_buffer(on_score_line=True)
                if pending_home is None and pending_away is None:
                    continue
                pending_scores = (int(score_match.group("home")), int(score_match.group("away")))
                awaiting_away = pending_away is None
                continue

            if self._is_team_fragment(line):
                if pending_home is not None and pending_away is not None and not awaiting_away:
                    finalize_fixture()
                team_buffer.append(line)
                continue

            consume_team_buffer()
            finalize_fixture()

        consume_team_buffer()
        finalize_fixture()

        return fixtures

    def _normalise_date(self, raw_date: str) -> str:
        """Return the ISO formatted representation of ``raw_date`` when possible."""

        cleaned = raw_date.strip()
        if not cleaned:
            return cleaned

        normalized = cleaned.replace("/", "-")
        for pattern in ("%d-%m-%Y", "%d-%m-%y"):
            try:
                parsed = datetime.strptime(normalized, pattern)
            except ValueError:
                continue
            return parsed.strftime("%Y-%m-%d")
        return normalized

    def _normalise_whitespace(self, text: str) -> str:
        """Collapse whitespace and exotic spaces in a line."""

        cleaned = (
            text.replace("\u00A0", " ")
            .replace("\u2007", " ")
            .replace("\u202F", " ")
            .strip()
        )
        return re.sub(r"\s+", " ", cleaned)

    def _normalise_team_name(self, fragments: List[str]) -> str:
        """Join and clean raw text fragments describing a team name."""

        text = " ".join(fragments)
        text = _DATE_RE.sub(" ", text)
        text = _TIME_RE.sub(" ", text)
        if text.lower().startswith("descansa"):
            text = text.split(" ", 1)[1] if " " in text else ""
        if text.lower().endswith(" descansa"):
            text = text[: -len(" descansa")]
        text = text.replace("Campo:", " ")
        text = text.replace("Campo", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip(" -,:")

    def _is_team_fragment(self, line: str) -> bool:
        """Return True when the line contains a fragment of a team name."""

        lower_line = line.lower()
        if any(lower_line.startswith(prefix) for prefix in _METADATA_PREFIXES):
            return False
        if _SCORE_ONLY_RE.match(line):
            return False
        cleaned = self._normalise_team_name([line])
        if not cleaned:
            return False
        return any(char.isalpha() for char in cleaned)
