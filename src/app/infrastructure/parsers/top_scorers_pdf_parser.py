"""Parser that extracts top scorers information from competition PDFs."""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from app.application.process_document import DocumentParser
from app.application.process_top_scorers import TopScorersParser
from app.domain.models.document import ParsedDocument
from app.domain.models.top_scorers import TopScorerEntry, TopScorersTable
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser

_ROW_END_PATTERN = re.compile(r"^\d+,\d+$")
_PENALTY_PATTERN = re.compile(r"\((\d+)\s+de\s+penalti", re.IGNORECASE)
_GROUP_KEYWORDS = {
    "grupo",
    "gr.",
    "gr",
    "preferente",
    "aficionados",
    "benjamin",
    "alevin",
    "infantil",
    "cadete",
    "juvenil",
    "senior",
    "honor",
    "regional",
    "liga",
    "division",
    "primera",
    "segunda",
    "tercera",
    "cuarta",
}
_TEAM_KEYWORDS = {
    "REAL",
    "UNION",
    "UNIÓN",
    "CLUB",
    "ATLETICO",
    "ATLÉTICO",
    "DEPORTIVO",
    "SPORTING",
    "CF",
    "C.F",
    "C.F.",
    "CD",
    "C.D",
    "C.D.",
    "UD",
    "U.D",
    "U.D.",
    "AD",
    "A.D",
    "A.D.",
    "FC",
    "F.C",
    "F.C.",
    "AC",
    "A.C",
    "A.C.",
    "ESC",
    "ESC.",
    "ESCOLA",
    "ACADEMIA",
    "ACADEMY",
    "JUVENTUD",
    "TABERNA",
    "CAFETERIA",
    "CAFETERÍA",
    "NEW",
    "GOLDEN",
    "CHESTERFIELD",
    "JUNIOR",
    "SHOTS",
    "RAIMON",
    "SATIUT",
    "ACADEMIA",
    "ACADEMY",
    "ATLETIC",
    "ATHLETIC",
}
_FOOTER_PREFIXES = (
    "DELEGACION",
    "DELEGACIÓN",
    "R.F.F.M",
    "FEDERACION",
    "FEDERACIÓN",
)


class TopScorersPdfParser(TopScorersParser):
    """Decode top scorers information from uploaded PDF documents."""

    def __init__(self, document_parser: DocumentParser | None = None) -> None:
        """Initialize the parser optionally providing a custom document parser."""

        self._document_parser = document_parser or PdfDocumentParser()

    def parse(self, document_bytes: bytes) -> TopScorersTable:
        """Parse the PDF bytes and return the top scorers table."""

        parsed_document = self._document_parser.parse(document_bytes)
        lines = list(_iterate_lines(parsed_document))
        metadata = _extract_metadata(lines)
        row_groups = _extract_row_groups(lines)

        if not row_groups:
            raise ValueError("No scorer entries were found in the provided PDF.")

        entries = [
            _parse_row(tokens, raw_lines, metadata.default_group)
            for tokens, raw_lines in row_groups
        ]

        indexed_entries = list(enumerate(entries))
        indexed_entries.sort(
            key=lambda item: (-_goals_value(item[1]), item[0])
        )
        sorted_entries = [entry for _, entry in indexed_entries]

        return TopScorersTable(
            title=metadata.title,
            competition=metadata.competition,
            category=metadata.category,
            season=metadata.season,
            scorers=sorted_entries,
        )


class _TableMetadata:
    """Represent metadata extracted from the table header."""

    def __init__(
        self,
        title: Optional[str],
        competition: Optional[str],
        category: Optional[str],
        season: Optional[str],
    ) -> None:
        self.title = title
        self.competition = competition
        self.category = category
        self.season = season

    @property
    def default_group(self) -> Optional[str]:
        """Return the default group value when the table has a single group."""

        return self.category


def _iterate_lines(parsed_document: ParsedDocument) -> Iterable[str]:
    """Yield normalized lines from the parsed document."""

    for page in parsed_document.pages:
        for line in page.content:
            normalized = line.strip()
            if normalized:
                yield normalized


def _extract_metadata(lines: Sequence[str]) -> _TableMetadata:
    """Extract header metadata from the provided lines."""

    header_line = next((line for line in lines if "Temporada" in line), "")
    title = header_line.strip() or None
    competition: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None

    if header_line:
        before, _, after = header_line.partition("Temporada")
        season = after.strip() or None
        title_part = before.strip().strip(",")
        if "," in title_part:
            first, _, remainder = title_part.partition(",")
            competition = first.strip() or None
            category = remainder.strip() or None
        else:
            competition = title_part or None

    return _TableMetadata(title, competition, category, season)


def _extract_row_groups(lines: Sequence[str]) -> List[Tuple[List[str], List[str]]]:
    """Collect token and raw line groups describing each table row."""

    start_index = _locate_table_start(lines)
    groups: List[Tuple[List[str], List[str]]] = []
    current_tokens: List[str] = []
    current_lines: List[str] = []

    for line in lines[start_index:]:
        if _is_footer_line(line):
            break

        tokens = line.split()
        if not tokens:
            continue

        current_lines.append(line)
        current_tokens.extend(tokens)

        if _ROW_END_PATTERN.match(tokens[-1]):
            groups.append((current_tokens, current_lines))
            current_tokens = []
            current_lines = []

    return groups


def _locate_table_start(lines: Sequence[str]) -> int:
    """Return the index where the scorer rows begin."""

    header_index = next(
        (index for index, line in enumerate(lines) if "Jugador" in line and "Equipo" in line),
        None,
    )
    if header_index is None:
        return 0

    index = header_index + 1
    while index < len(lines) and _is_header_line(lines[index]):
        index += 1
    return index


def _is_header_line(line: str) -> bool:
    """Return ``True`` when the line belongs to the table header block."""

    lowered = line.lower()
    return "jugados" in lowered or "goles" in lowered or "partido" in lowered


def _is_footer_line(line: str) -> bool:
    """Return ``True`` when the line corresponds to a footer."""

    normalized = line.strip().upper()
    return any(normalized.startswith(prefix) for prefix in _FOOTER_PREFIXES)


def _parse_row(tokens: List[str], raw_lines: List[str], default_group: Optional[str]) -> TopScorerEntry:
    """Parse a single row returning the corresponding scorer entry."""

    if len(tokens) < 4:
        raise ValueError("Incomplete scorer row detected in the PDF.")

    goals_per_match_token = tokens[-1]
    core_tokens = tokens[:-1]

    match_index = next((index for index, token in enumerate(core_tokens) if token.isdigit()), None)
    if match_index is None:
        raise ValueError("Unable to locate matches played in scorer row.")

    matches_token = core_tokens[match_index]
    goals_tokens = core_tokens[match_index + 1 :]
    identity_tokens = core_tokens[:match_index]

    player, team, group = _split_identity_tokens(identity_tokens)
    if group is None:
        group = default_group

    goals_details = " ".join(goals_tokens).strip() or None
    goals_total = _extract_goals_total(goals_tokens)
    penalty_goals = _extract_penalty(goals_tokens)
    goals_per_match = _parse_float_token(goals_per_match_token)
    matches_played = _parse_int_token(matches_token)

    return TopScorerEntry(
        player=player,
        team=team,
        group=group,
        matches_played=matches_played,
        goals_total=goals_total,
        goals_details=goals_details,
        penalty_goals=penalty_goals,
        goals_per_match=goals_per_match,
        raw_lines=list(raw_lines),
    )


def _split_identity_tokens(tokens: Sequence[str]) -> Tuple[str, Optional[str], Optional[str]]:
    """Split identity tokens into player, team and group components."""

    if not tokens:
        return "", None, None

    group_index = _find_group_start(tokens)
    if group_index is not None:
        group_tokens = tokens[group_index:]
        name_team_tokens = tokens[:group_index]
    else:
        group_tokens = []
        name_team_tokens = list(tokens)

    player_tokens, team_tokens = _split_player_and_team(name_team_tokens)
    player = " ".join(player_tokens).strip()
    team = " ".join(team_tokens).strip() or None
    group = " ".join(group_tokens).strip() or None
    return player, team, group


def _find_group_start(tokens: Sequence[str]) -> Optional[int]:
    """Return the index where the group information begins when present."""

    for index, token in enumerate(tokens):
        normalized = token.lower()
        if "f-" in normalized:
            return index
        if any(char.isdigit() for char in token) and ("ª" in token or "º" in token):
            return index
        if normalized in _GROUP_KEYWORDS:
            return index
    return None


def _split_player_and_team(tokens: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Return separate token lists for player and team names."""

    if not tokens:
        return [], []

    player_tokens: List[str] = []
    team_tokens: List[str] = []
    seen_comma = False
    given_after_comma = 0

    for index, token in enumerate(tokens):
        normalized = token.strip(",.").upper()
        if not seen_comma:
            player_tokens.append(token)
            if "," in token:
                seen_comma = True
            continue

        if not team_tokens:
            if normalized in _TEAM_KEYWORDS:
                team_tokens.append(token)
                continue
            if given_after_comma >= 1 and index == len(tokens) - 1:
                team_tokens.append(token)
                continue
            if given_after_comma >= 2:
                team_tokens.append(token)
                continue
            player_tokens.append(token)
            given_after_comma += 1
            continue

        team_tokens.append(token)

    if not seen_comma and tokens:
        return list(tokens), []

    if not team_tokens and len(tokens) > len(player_tokens):
        team_tokens = list(tokens[len(player_tokens) :])

    return player_tokens, team_tokens


def _extract_goals_total(tokens: Sequence[str]) -> Optional[int]:
    """Return the total goals recorded within the row."""

    for token in tokens:
        match = re.search(r"(\d+)", token)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def _extract_penalty(tokens: Sequence[str]) -> Optional[int]:
    """Return the penalty goal count when available."""

    details = " ".join(tokens)
    match = _PENALTY_PATTERN.search(details)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _parse_float_token(token: str) -> Optional[float]:
    """Return a float converted from a numeric token using comma decimals."""

    normalized = token.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _parse_int_token(token: str) -> Optional[int]:
    """Return an integer converted from the provided token."""

    try:
        return int(token)
    except ValueError:
        return None


def _goals_value(entry: TopScorerEntry) -> int:
    """Return a sortable goal value prioritising rows with available data."""

    return entry.goals_total if entry.goals_total is not None else -1

