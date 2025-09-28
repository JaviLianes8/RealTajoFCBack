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


TEAM_LINE_PATTERN = re.compile(r"^(\d+)\.\-\s+(.+)$")


def _extract_team_names(lines: Sequence[str]) -> List[str]:
    """Collect the registered team names listed in the calendar."""

    team_names: List[str] = []
    capture = False
    current_entry: List[str] = []
    for line in lines:
        if not capture and line.lower().startswith("equipos participantes"):
            capture = True
            continue
        if capture:
            if line.lower().startswith("delegacion"):
                if current_entry:
                    _append_team_name(team_names, current_entry)
                break
            match = TEAM_LINE_PATTERN.match(line)
            if match:
                if current_entry:
                    _append_team_name(team_names, current_entry)
                current_entry = [match.group(2).strip()]
                if _looks_like_complete_entry(current_entry[-1]):
                    _append_team_name(team_names, current_entry)
                    current_entry = []
            elif current_entry:
                current_entry.append(line.strip())
                if _looks_like_complete_entry(current_entry[-1]):
                    _append_team_name(team_names, current_entry)
                    current_entry = []
    if current_entry:
        _append_team_name(team_names, current_entry)
    if "REAL TAJO" not in team_names:
        team_names.append("REAL TAJO")
    return team_names


def _looks_like_complete_entry(line: str) -> bool:
    """Return ``True`` when ``line`` finishes a team entry."""

    return bool(re.search(r"\(\d+\)\s*$", line))


def _append_team_name(team_names: List[str], parts: List[str]) -> None:
    """Append the normalized team name composed of ``parts`` into ``team_names``."""

    raw_name = " ".join(parts).strip()
    normalized = re.sub(r"\s*\(\d+\)\s*$", "", raw_name).strip()
    if normalized:
        team_names.append(normalized)


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
    pending_matchday: Optional[int] = None
    jornada_lines: List[str] = []

    jornada_pattern = re.compile(r"Jornada\s+(\d+)\s*\((\d{2}-\d{2}-\d{4})\)")
    jornada_without_date_pattern = re.compile(r'Jornada\s+(\d+)(?!\s*\()')
    date_pattern = re.compile(r"\((\d{2}-\d{2}-\d{4})\)")

    def finalize_current_jornada() -> None:
        """Persist the Real Tajo match gathered for the current jornada."""

        nonlocal jornada_lines

        if (
            current_stage is None
            or current_matchday is None
            or current_date is None
            or not jornada_lines
        ):
            jornada_lines = []
            return

        parsed = _parse_real_tajo_match_from_lines(
            jornada_lines, sorted_names, real_tajo_name
        )
        jornada_lines = []
        if parsed is None:
            return

        home_team, away_team = parsed
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

    for line in lines:
        lower_line = line.lower()

        if _is_stage_line(lower_line):
            finalize_current_jornada()
            current_stage = "Primera Vuelta" if "primera vuelta" in lower_line else "Segunda Vuelta"
            current_matchday = None
            current_date = None
            pending_matchday = None

        jornada_match = jornada_pattern.search(line)
        if jornada_match:
            finalize_current_jornada()
            current_matchday = int(jornada_match.group(1))
            current_date = datetime.strptime(jornada_match.group(2), "%d-%m-%Y")
            pending_matchday = None
            jornada_lines = []
            remaining = line[jornada_match.end() :].strip()
            if remaining:
                jornada_lines.append(remaining)
            continue

        jornada_without_date_match = jornada_without_date_pattern.search(line)
        if jornada_without_date_match:
            finalize_current_jornada()
            current_matchday = int(jornada_without_date_match.group(1))
            current_date = None
            pending_matchday = current_matchday
            jornada_lines = []
            remaining = line[jornada_without_date_match.end() :].strip()
            if remaining:
                jornada_lines.append(remaining)
            continue

        if pending_matchday is not None and current_date is None:
            date_match = date_pattern.search(line)
            if date_match:
                current_date = datetime.strptime(date_match.group(1), "%d-%m-%Y")
                pending_matchday = None
                leading = line[: date_match.start()].strip()
                trailing = line[date_match.end() :].strip()
                if leading:
                    jornada_lines.append(leading)
                if trailing:
                    jornada_lines.append(trailing)
                continue

        if (
            current_stage is None
            or current_matchday is None
            or current_date is None
            or not line
        ):
            continue

        if line.startswith("Calendario de Competiciones") or line.startswith("DELEGACION"):
            continue

        jornada_lines.append(line)

    finalize_current_jornada()

    return matches


def _is_stage_line(lower_line: str) -> bool:
    """Return ``True`` when the provided line represents a competition stage."""

    return "primera vuelta" in lower_line or "segunda vuelta" in lower_line


def _parse_real_tajo_match_from_lines(
    jornada_lines: Sequence[str],
    team_names: Sequence[str],
    real_tajo_name: str,
) -> Optional[Tuple[str, str]]:
    """Find the Real Tajo fixture within the accumulated jornada lines."""

    if not jornada_lines:
        return None

    combined = " ".join(jornada_lines).strip()
    candidates: List[str] = []
    if combined:
        candidates.append(combined)
    candidates.extend(
        line for line in jornada_lines if "REAL TAJO" in line.upper()
    )

    seen_candidates: set[str] = set()
    for candidate in candidates:
        normalized_candidate = candidate.strip()
        if not normalized_candidate or normalized_candidate in seen_candidates:
            continue
        seen_candidates.add(normalized_candidate)
        parsed = _parse_real_tajo_match_from_text(
            normalized_candidate, team_names, real_tajo_name
        )
        if parsed is not None:
            return parsed

    return None


def _parse_real_tajo_match_from_text(
    text: str, team_names: Sequence[str], real_tajo_name: str
) -> Optional[Tuple[str, str]]:
    """Extract the Real Tajo pairing from ``text`` using team delimiters."""

    if "REAL TAJO" not in text.upper():
        return None

    search_names = list(team_names)
    if "DESCANSA" not in {name.upper() for name in search_names}:
        search_names.append("DESCANSA")

    occurrences = _collect_team_occurrences(text, search_names)
    if not occurrences:
        return None

    normalized_real = _normalize_for_matching(real_tajo_name)
    dash_positions = [match.start() for match in re.finditer(r"[-–—]", text)]

    for dash_index in dash_positions:
        left = _find_adjacent_team_left(occurrences, text, dash_index)
        right = _find_adjacent_team_right(occurrences, text, dash_index)
        if left is None or right is None:
            continue

        left_team = left[2]
        right_team = right[2]

        normalized_left = _normalize_for_matching(left_team)
        normalized_right = _normalize_for_matching(right_team)

        if normalized_real not in {normalized_left, normalized_right}:
            continue

        if {
            normalized_left,
            normalized_right,
        } == {normalized_real, _normalize_for_matching("Descansa")}:
            return (
                real_tajo_name if normalized_left == normalized_real else "Descansa",
                real_tajo_name if normalized_right == normalized_real else "Descansa",
            )

        if _normalize_for_matching("Descansa") in {normalized_left, normalized_right}:
            continue

        return (
            real_tajo_name if normalized_left == normalized_real else left_team,
            real_tajo_name if normalized_right == normalized_real else right_team,
        )

    fallback = _parse_real_tajo_match_with_unknown_team(text, real_tajo_name)
    if fallback is not None:
        return fallback

    return None


def _collect_team_occurrences(
    text: str, team_names: Sequence[str]
) -> List[Tuple[int, int, str]]:
    """Collect ordered team name occurrences found within ``text``."""

    occurrences: List[Tuple[int, int, str]] = []
    length = len(text)

    for start in range(length):
        snippet = text[start:]
        for team_name in team_names:
            consumed = _match_prefix(snippet, team_name)
            if consumed is None:
                continue
            occurrences.append((start, start + consumed, team_name))
            break

    deduped: List[Tuple[int, int, str]] = []
    previous_start = -1
    for occurrence in occurrences:
        if occurrence[0] == previous_start:
            continue
        deduped.append(occurrence)
        previous_start = occurrence[0]

    return deduped


def _find_adjacent_team_left(
    occurrences: Sequence[Tuple[int, int, str]], text: str, dash_index: int
) -> Optional[Tuple[int, int, str]]:
    """Return the team immediately to the left of the separator at ``dash_index``."""

    for start, end, name in reversed(occurrences):
        if end > dash_index:
            continue
        between = text[end:dash_index]
        if any(character.isalnum() for character in between):
            continue
        return start, end, name
    return None


def _find_adjacent_team_right(
    occurrences: Sequence[Tuple[int, int, str]], text: str, dash_index: int
) -> Optional[Tuple[int, int, str]]:
    """Return the team immediately to the right of the separator at ``dash_index``."""

    for start, end, name in occurrences:
        if start < dash_index:
            continue
        between = text[dash_index + 1 : start]
        if any(character.isalnum() for character in between):
            continue
        return start, end, name
    return None


def _parse_real_tajo_match_with_unknown_team(
    text: str, real_tajo_name: str
) -> Optional[Tuple[str, str]]:
    """Fallback extraction for fixtures where the opponent is missing from participants."""

    normalized_real = _normalize_for_matching(real_tajo_name)
    descansa_marker = _normalize_for_matching("Descansa")

    for index, character in enumerate(text):
        if character not in "-–—":
            continue

        left_raw = text[:index]
        right_raw = text[index + 1 :]

        home_candidate = _sanitize_team_segment(left_raw)
        away_candidate = _sanitize_team_segment(right_raw)

        if not home_candidate or not away_candidate:
            continue

        normalized_home = _normalize_for_matching(home_candidate)
        normalized_away = _normalize_for_matching(away_candidate)

        if normalized_real not in {normalized_home, normalized_away}:
            continue

        if {normalized_home, normalized_away} == {normalized_real, descansa_marker}:
            return (
                real_tajo_name if normalized_home == normalized_real else "Descansa",
                real_tajo_name if normalized_away == normalized_real else "Descansa",
            )

        if descansa_marker in {normalized_home, normalized_away}:
            continue

        return (
            real_tajo_name if normalized_home == normalized_real else home_candidate,
            real_tajo_name if normalized_away == normalized_real else away_candidate,
        )

    return None


def _sanitize_team_segment(segment: str) -> str:
    """Trim auxiliary markers and punctuation from a potential team name segment."""

    cleaned = segment.strip()
    cleaned = cleaned.strip("-–—,.;")
    cleaned = re.sub(r"\(\d{2}-\d{2}-\d{4}\).*", "", cleaned)
    cleaned = re.sub(r"Jornada\s+\d+.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(Primera|Segunda)\s+Vuelta.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split("Descansa")[-1]
    cleaned = cleaned.strip()
    return cleaned


def _match_prefix(text: str, candidate: str) -> Optional[int]:
    """Return the length of ``candidate`` within ``text`` ignoring case and accents."""

    normalized_candidate = _normalize_for_matching(candidate)
    if not normalized_candidate:
        return None

    normalized_so_far = ""
    consumed = 0

    for char in text:
        normalized_char = _normalize_for_matching(char)
        if not normalized_char:
            consumed += 1
            continue

        tentative = normalized_so_far + normalized_char
        if not normalized_candidate.startswith(tentative):
            return None

        normalized_so_far = tentative
        consumed += 1

        if normalized_so_far == normalized_candidate:
            return consumed

    return None


def _normalize_for_matching(text: str) -> str:
    """Uppercase ``text`` removing accent marks to support fuzzy comparisons."""

    normalized = unicodedata.normalize("NFD", text)
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return stripped.upper()


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
