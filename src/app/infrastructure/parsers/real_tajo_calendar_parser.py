"""Parser that extracts Real Tajo specific information from competition PDFs."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple

from app.application.process_document import DocumentParser
from app.application.process_real_tajo_calendar import RealTajoCalendarParser
from app.domain.models.document import ParsedDocument
from app.domain.models.real_tajo_calendar import (
    RealTajoCalendar,
    RealTajoKit,
    RealTajoMatch,
    RealTajoTeamInfo,
)
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser


class RealTajoCalendarPdfParser(RealTajoCalendarParser):
    """Decode Real Tajo calendar information from uploaded PDF documents."""

    def __init__(self, document_parser: DocumentParser | None = None) -> None:
        """Initialize the parser optionally providing a custom document parser."""

        self._document_parser = document_parser or PdfDocumentParser()

    def parse(self, document_bytes: bytes) -> RealTajoCalendar:
        """Parse the PDF bytes and return the Real Tajo calendar model."""

        parsed_document = self._document_parser.parse(document_bytes)
        lines = list(_iterate_lines(parsed_document))

        competition, season = _extract_competition_and_season(lines)
        team_names = _extract_team_names(lines)
        matches = _extract_real_tajo_matches(lines, team_names)
        team_info = _extract_team_info(lines)

        if not matches:
            raise ValueError("No Real Tajo fixtures were found in the provided calendar.")

        if team_info is None:
            team_info = RealTajoTeamInfo(name="REAL TAJO")

        return RealTajoCalendar(
            competition=competition,
            season=season,
            matches=matches,
            team_info=team_info,
        )


def _iterate_lines(parsed_document: ParsedDocument) -> Iterable[str]:
    """Yield normalized lines from the parsed document."""

    for page in parsed_document.pages:
        for line in page.content:
            normalized = _normalize_text(line)
            if normalized:
                yield normalized


def _normalize_text(text: str) -> str:
    """Collapse whitespace within ``text`` and strip leading or trailing spaces."""

    collapsed = " ".join(text.replace("\xa0", " ").split())
    return collapsed.strip()


def _extract_competition_and_season(lines: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
    """Retrieve competition name and season from the document header."""

    for line in lines:
        if "Temporada" not in line:
            continue
        parts = line.split("Temporada", maxsplit=1)
        if len(parts) != 2:
            continue
        competition = parts[0].rstrip(", ") or None
        season = parts[1].strip() or None
        return competition, season
    return None, None


TEAM_LINE_PATTERN = re.compile(r"^(\d+)\.\-\s+(.+?)\s*(?:\(\d+\))?$")


def _extract_team_names(lines: Sequence[str]) -> List[str]:
    """Collect the registered team names listed in the calendar."""

    team_names: List[str] = []
    capture = False
    for line in lines:
        if not capture and line.lower().startswith("equipos participantes"):
            capture = True
            continue
        if capture:
            if line.lower().startswith("delegacion"):
                break
            match = TEAM_LINE_PATTERN.match(line)
            if match:
                team_names.append(match.group(2).strip())
    if "REAL TAJO" not in team_names:
        team_names.append("REAL TAJO")
    return team_names


def _extract_real_tajo_matches(lines: Sequence[str], team_names: Sequence[str]) -> List[RealTajoMatch]:
    """Extract and filter matches that involve Real Tajo from the schedule."""

    sorted_names = sorted(team_names, key=len, reverse=True)
    real_tajo_name = next(
        (team for team in team_names if "REAL TAJO" in team.upper()),
        "REAL TAJO",
    )

    matches: List[RealTajoMatch] = []
    current_stage: Optional[str] = None
    current_matchday: Optional[int] = None
    current_date: Optional[datetime] = None
    buffer = ""

    jornada_pattern = re.compile(r"Jornada\s+(\d+)\s*\((\d{2}-\d{2}-\d{4})\)")

    for line in lines:
        lower_line = line.lower()
        if "primera vuelta" in lower_line:
            current_stage = "Primera Vuelta"
            current_matchday = None
            buffer = ""

        if "segunda vuelta" in lower_line:
            current_stage = "Segunda Vuelta"
            current_matchday = None
            buffer = ""

        jornada_match = jornada_pattern.search(line)
        if jornada_match:
            current_matchday = int(jornada_match.group(1))
            current_date = datetime.strptime(jornada_match.group(2), "%d-%m-%Y")
            buffer = ""
            remaining = line[jornada_match.end() :].strip()
            if remaining:
                buffer = remaining

        if current_stage is None or current_matchday is None or current_date is None:
            continue

        if line.startswith("Calendario de Competiciones") or line.startswith("DELEGACION"):
            continue

        if not jornada_match and not _is_stage_line(lower_line):
            buffer = f"{buffer} {line}".strip() if buffer else line

        buffer = buffer.strip()
        while buffer:
            parsed_match = _parse_match(buffer, sorted_names)
            if parsed_match is None:
                break

            home_team, away_team, consumed = parsed_match
            buffer = buffer[consumed:].lstrip(" -,.\n")

            if real_tajo_name not in (home_team, away_team):
                continue

            opponent = away_team if home_team == real_tajo_name else home_team
            matches.append(
                RealTajoMatch(
                    stage=current_stage,
                    matchday=current_matchday,
                    match_date=current_date.date(),
                    opponent=opponent,
                    is_home=home_team == real_tajo_name,
                )
            )

    return matches


def _is_stage_line(lower_line: str) -> bool:
    """Return ``True`` when the provided line represents a competition stage."""

    return "primera vuelta" in lower_line or "segunda vuelta" in lower_line


def _parse_match(text: str, team_names: Sequence[str]) -> Optional[Tuple[str, str, int]]:
    """Attempt to extract the next match from ``text`` splitting by known team names."""

    if " - " not in text:
        return None

    for home_team in team_names:
        prefix = f"{home_team} - "
        if not text.startswith(prefix):
            continue
        remainder = text[len(prefix) :]
        for away_team in team_names:
            if remainder.startswith(away_team):
                consumed = len(prefix) + len(away_team)
                return home_team, away_team, consumed
    return None


KIT_PAIR_PATTERN = re.compile(
    r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9ºª'().-]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9ºª'().-]+)*):\s*"
    r"([^:]+?)(?=(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9ºª'().-]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9ºª'().-]+)*:)|$)"
)


def _extract_team_info(lines: Sequence[str]) -> Optional[RealTajoTeamInfo]:
    """Extract contact and kit information specific to Real Tajo."""

    for index, line in enumerate(lines):
        if not line.upper().startswith("REAL TAJO"):
            continue

        has_contact_marker = "Contacto" in line
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if not has_contact_marker and "Contacto" not in next_line:
            continue

        contact_name: Optional[str] = None
        phone: Optional[str] = None
        address: Optional[str] = None

        contact_match = re.search(r"Contacto:\s*(.+)", line)
        if contact_match:
            contact_name = contact_match.group(1).strip() or None

        lookahead = index + 1
        if contact_name is None and lookahead < len(lines):
            contact_line = lines[lookahead]
            if "Contacto:" in contact_line:
                contact_name = contact_line.split("Contacto:", maxsplit=1)[1].strip() or None
                lookahead += 1

        if lookahead < len(lines):
            potential_address = lines[lookahead]
            if not potential_address.startswith("Teléfono"):
                address = potential_address
                lookahead += 1

        if lookahead < len(lines) and "Teléfono" in lines[lookahead]:
            phone = lines[lookahead].split("Teléfono:", maxsplit=1)[1].strip() or None
            lookahead += 1

        first_kit, offset = _parse_kit_section(lines, lookahead)
        lookahead += offset
        second_kit, _ = _parse_kit_section(lines, lookahead)

        return RealTajoTeamInfo(
            name="REAL TAJO",
            contact_name=contact_name,
            phone=phone,
            address=address,
            first_kit=first_kit,
            second_kit=second_kit,
        )

    return None


def _parse_kit_section(
    lines: Sequence[str], start_index: int
) -> Tuple[RealTajoKit, int]:
    """Parse a kit section starting at ``start_index`` returning the kit and consumed lines."""

    if start_index >= len(lines):
        return RealTajoKit(), 0

    title = lines[start_index]
    if "equipación" not in title.lower():
        return RealTajoKit(), 0

    consumed = 1
    type_line: Optional[str] = None
    color_line: Optional[str] = None

    if start_index + consumed < len(lines) and "Tipo" in lines[start_index + consumed]:
        type_line = lines[start_index + consumed]
        consumed += 1

    if start_index + consumed < len(lines):
        color_line = lines[start_index + consumed]
        consumed += 1

    kit = RealTajoKit()
    if type_line or color_line:
        kit = _build_kit(type_line, color_line)

    return kit, consumed


def _build_kit(type_line: Optional[str], color_line: Optional[str]) -> RealTajoKit:
    """Create a ``RealTajoKit`` instance from type and color lines."""

    type_pairs = _parse_pairs(type_line) if type_line else {}
    color_pairs = _parse_pairs(color_line) if color_line else {}

    return RealTajoKit(
        shirt=color_pairs.get("camiseta"),
        shorts=color_pairs.get("pantalon"),
        socks=color_pairs.get("medias"),
        shirt_type=type_pairs.get("tipo_camiseta"),
        shorts_type=type_pairs.get("tipo_pantalon"),
        socks_type=type_pairs.get("tipo_medias"),
    )


def _parse_pairs(line: str) -> dict[str, str]:
    """Parse key-value pairs within ``line`` produced by the PDF extractor."""

    pairs: dict[str, str] = {}
    for raw_key, raw_value in KIT_PAIR_PATTERN.findall(line):
        key = _normalize_key(raw_key)
        value = raw_value.strip()
        if key:
            pairs[key] = value
    return pairs


def _normalize_key(key: str) -> str:
    """Normalize a raw key removing accents and special characters."""

    normalized = unicodedata.normalize("NFD", key)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    cleaned = without_accents.replace("º", "").replace("ª", "").replace("'", "")
    cleaned = cleaned.replace(".", "").replace("-", " ").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.replace(" ", "_")
