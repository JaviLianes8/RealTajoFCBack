"""Universal PDF table parser for top scorers (exports TopScorersPdfParser).

This module keeps the original import path and class name expected by the app:
    app.infrastructure.parsers.top_scorers_pdf_parser.TopScorersPdfParser

It parses RFFM-like PDFs into TopScorersTable while ignoring "Grupo/División".
It is tolerant to:
  - Glued tokens like 'F-11242,0000'
  - Broken '(1 de\npenalti)'
  - Extra group/category words
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from app.application.process_document import DocumentParser
from app.application.process_top_scorers import TopScorersParser
from app.domain.models.document import ParsedDocument
from app.domain.models.top_scorers import TopScorerEntry, TopScorersTable
from app.infrastructure.parsers.pdf_document_parser import PdfDocumentParser


# ---------- regex helpers ----------
_RE_SPACES = re.compile(r"\s+")
_RE_RATIO_LAST = re.compile(r"(\d+[,.]\d+)(?!.*\d+[,.]\d+)")
_RE_INT = re.compile(r"\d+")
_RE_PEN = re.compile(r"\(\s*(\d+)\s+de\s+penalti\s*\)", re.IGNORECASE)

_TEAM_HINTS = {
    "REAL","UNION","UNIÓN","CLUB","ATLETICO","ATLÉTICO","DEPORTIVO","SPORTING",
    "CF","C.F","C.F.","CD","C.D","C.D.","UD","U.D","U.D.","AD","A.D","A.D.",
    "FC","F.C","F.C.","AC","A.C","A.C.","ESC","ESC.","ESCOLA","ACADEMIA","ACADEMY",
    "JUVENTUD","TABERNA","CAFETERIA","CAFETERÍA","NEW","GOLDEN","CHESTERFIELD",
    "JUNIOR","SHOTS","RAIMON","SATIUT","ATLETIC","ATHLETIC",
}
_DROP_TAIL = {
    "aficionados","preferente","regional","liga","division","división",
    "primera","segunda","tercera","cuarta","grupo","gr.","gr","f-11","f",
}
_FOOTER_PREFIXES = ("DELEGACION", "DELEGACIÓN", "R.F.F.M", "RFFM", "FEDERACION", "FEDERACIÓN")


def _norm(text: str) -> str:
    """Collapse exotic/multiple spaces."""
    collapsed = _RE_SPACES.sub(
        " ",
        text.replace("\u00A0", " ").replace("\u2007", " ").replace("\u202F", " "),
    ).strip()
    return re.sub(r"\s+(?=[ºª])", "", collapsed)


def _pre_norm(line: str) -> str:
    """Insert spaces between letters/digits and after 'F-11' to break glued tokens."""
    t = _norm(line)
    t = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])(?=\d)", " ", t)
    t = re.sub(r"(?<=\d)(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", " ", t)
    t = re.sub(r"(?<=\))(?=\d)", " ", t)
    t = re.sub(r"(?<=F-11)(?=\d)", " ", t)
    return t


def _iter_lines(parsed: ParsedDocument) -> Iterable[str]:
    """Yield normalized lines from the parsed PDF."""
    for page in parsed.pages:
        for raw in page.content:
            line = _pre_norm(raw.strip())
            if line:
                yield line


def _is_header_block(line: str) -> bool:
    """Return True if line is part of the column header area."""
    low = line.lower()
    return ("jugador" in low and "equipo" in low) or "goles" in low or "partido" in low or "jugados" in low


def _is_footer(line: str) -> bool:
    """Return True if the line is a footer we should stop at."""
    up = line.strip().upper()
    return any(up.startswith(p) for p in _FOOTER_PREFIXES) or "R.F.F.M" in up or "RFFM" in up


def _collect_rows(lines: List[str]) -> List[Tuple[str, str]]:
    """Return (identity_text, stats_text) pairs using 'F-11' as the stats marker."""
    rows: List[Tuple[str, str]] = []
    cur_ident: List[str] = []
    cur_stats: List[str] = []
    in_stats = False

    def flush():
        ident = _norm(" ".join(cur_ident))
        stats = _norm(" ".join(cur_stats))
        if ident and stats:
            rows.append((ident, stats))

    # skip header block
    it = iter(lines)
    for ln in it:
        if _is_header_block(ln):
            break
    # consume the rest
    for ln in it:
        if _is_footer(ln):
            break
        if _is_header_block(ln):
            continue
        if not in_stats:
            cur_ident.append(ln)
            if "F-11" in ln:
                a, b = ln.split("F-11", 1)
                cur_ident[-1] = _norm(a)
                cur_stats.append("F-11 " + _norm(b))
                in_stats = True
        else:
            if "F-11" in ln:
                cur_stats.append(ln)
            elif (
                "," in ln
                and "F-11" not in ln
                and not _is_header_block(ln)
                and any(ch.isupper() for ch in ln.split(",", 1)[0])
            ):
                flush()
                cur_ident, cur_stats, in_stats = [ln], [], False
            else:
                cur_stats.append(ln)

    if cur_ident and cur_stats:
        flush()
    return rows


def _trim_identity_tail(tokens: List[str]) -> List[str]:
    """Strip trailing division/group tokens and numbers from identity tail."""
    i = len(tokens)
    while i > 0:
        tok = tokens[i - 1]
        low = tok.lower().strip(",.;:/-")
        if (low in _DROP_TAIL) or low.isdigit() or low in {"ª", "º"}:
            i -= 1
            continue
        if low.endswith("ª") and low[:-1].isdigit():
            i -= 1
            continue
        break
    return tokens[:i]


def _split_player_team(identity_text: str) -> Tuple[str, Optional[str]]:
    """Split 'SURNAME, NAME TEAM...' -> (player, team)."""
    toks = [t for t in _norm(identity_text).replace("|", " ").split(" ") if t]
    toks = _trim_identity_tail(toks)
    if not toks:
        return "", None
    player: List[str] = []
    team: List[str] = []
    seen_comma = False
    after = 0
    for idx, tok in enumerate(toks):
        if not seen_comma:
            player.append(tok)
            if "," in tok:
                seen_comma = True
            continue
        if not team:
            if tok.strip(",.").upper() in _TEAM_HINTS or after >= 2 or (after >= 1 and idx == len(toks) - 1):
                team.append(tok)
            else:
                player.append(tok)
                after += 1
        else:
            team.append(tok)
    if not seen_comma:
        return " ".join(toks).strip(), None
    return " ".join(player).strip(), (" ".join(team).strip() or None)

def _parse_stats(stats_text: str) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[int], Optional[str]]:
    """Extract matches, goals, ratio and penalties from the stats block (robust)."""
    s = _norm(stats_text)
    if "F-11" in s:
        s = s.rsplit("F-11", 1)[1].strip()

    m_ratio = _RE_RATIO_LAST.search(s)
    ratio = float(m_ratio.group(1).replace(",", ".")) if m_ratio else None
    ratio_span = m_ratio.span(1) if m_ratio else None

    m_pen = _RE_PEN.search(s)
    penalties = int(m_pen.group(1)) if m_pen else None
    s_core = s
    if m_pen:
        a, b = m_pen.span()
        s_core = (s[:a] + " " + s[b:]).strip()

    ints: List[Tuple[int, str]] = []
    for m in _RE_INT.finditer(s_core):
        if ratio_span and ratio_span[0] <= m.start() < ratio_span[1]:
            continue
        ints.append((m.start(), m.group(0)))

    matches: Optional[int] = None
    goals: Optional[int] = None
    if not ints:
        pass
    elif len(ints) == 1:
        tok = ints[0][1]
        if len(tok) == 2:
            matches, goals = int(tok[0]), int(tok[1])
        else:
            matches = int(tok)
    else:
        tok0 = ints[0][1]
        tok1 = ints[1][1]
        if len(tok0) == 2 and (len(ints) == 2 or len(tok1) != 2):
            matches, goals = int(tok0[0]), int(tok0[1])
        else:
            matches, goals = int(tok0), int(tok1)

    details_parts: List[str] = []
    if goals is not None:
        details_parts.append(str(goals))
    if penalties is not None:
        details_parts.append(f"({penalties} de penalti)")
    details = " ".join(details_parts) if details_parts else None

    if ratio is None and matches is not None and goals is not None and matches != 0:
        ratio = goals / matches

    return matches, goals, ratio, penalties, details

class TopScorersPdfParser(TopScorersParser):
    """Decode top scorers information from uploaded PDF documents."""

    def __init__(self, document_parser: DocumentParser | None = None) -> None:
        """Initialize the parser (uses PdfDocumentParser by default)."""
        self._document_parser = document_parser or PdfDocumentParser()

    def parse(self, document_bytes: bytes) -> TopScorersTable:
        """Parse PDF bytes and return a TopScorersTable (group ignored)."""
        parsed_document = self._document_parser.parse(document_bytes)
        lines = list(_iter_lines(parsed_document))

        # metadata
        header_line = next((ln for ln in lines if "Temporada" in ln), "")
        title = header_line or None
        competition: Optional[str] = None
        category: Optional[str] = None
        season: Optional[str] = None
        if header_line:
            before, _, after = header_line.partition("Temporada")
            season = _norm(after) or None
            title_part = _norm(before).strip(",")
            if "," in title_part:
                first, _, rest = title_part.partition(",")
                competition = _norm(first) or None
                category = _norm(rest) or None
            else:
                competition = title_part or None

        # rows
        pairs = _collect_rows(lines)
        if not pairs:
            raise ValueError("No scorer entries were found in the provided PDF.")

        entries: List[TopScorerEntry] = []
        for ident, stats in pairs:
            player, team = _split_player_team(ident)
            matches, goals, ratio, penalties, details = _parse_stats(stats)
            entries.append(
                TopScorerEntry(
                    player=player,
                    team=team,
                    group=category,
                    matches_played=matches,
                    goals_total=goals,
                    goals_details=details,
                    penalty_goals=penalties,
                    goals_per_match=ratio,
                    raw_lines=[ident, stats],
                )
            )

        # stable sort by goals desc then original order
        indexed = list(enumerate(entries))
        indexed.sort(key=lambda it: (-(it[1].goals_total or -1), it[0]))
        scorers = [e for _, e in indexed]

        return TopScorersTable(
            title=title,
            competition=competition,
            category=category,
            season=season,
            scorers=scorers,
        )
