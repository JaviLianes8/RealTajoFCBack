"""Domain service that extracts Real Tajo information from a parsed document."""
from __future__ import annotations

import re
from typing import Iterable, List

from app.domain.models.document import ParsedDocument
from app.domain.models.real_tajo_calendar import (
    KitDetails,
    RealTajoCalendar,
    RealTajoFixture,
    TeamDetails,
)


class RealTajoCalendarExtractorService:
    """Build a Real Tajo calendar aggregate from a parsed document."""

    TEAM_NAME = "REAL TAJO"

    def extract(self, document: ParsedDocument) -> RealTajoCalendar:
        """Convert the provided document into a Real Tajo calendar aggregate."""

        if not document.pages:
            raise ValueError("The document does not contain any pages.")

        competition, season = self._extract_competition_and_season(document)
        fixtures = self._extract_fixtures(document)
        if not fixtures:
            raise ValueError("No fixtures for REAL TAJO were found in the document.")
        team_details = self._extract_team_details(document)

        return RealTajoCalendar(
            team=self.TEAM_NAME,
            competition=competition,
            season=season,
            fixtures=fixtures,
            team_details=team_details,
        )

    def _extract_competition_and_season(self, document: ParsedDocument) -> tuple[str, str]:
        for line in self._iter_lines(document):
            if "Temporada" in line:
                prefix, _, suffix = line.partition("Temporada")
                competition = prefix.strip(" ,")
                season = suffix.strip()
                if competition and season:
                    return competition, season
        raise ValueError("Unable to determine competition and season information.")

    def _extract_fixtures(self, document: ParsedDocument) -> List[RealTajoFixture]:
        fixtures: List[RealTajoFixture] = []
        stage = ""
        current_round: int | None = None
        current_date: str | None = None
        buffer = ""

        for line in self._iter_lines(document):
            normalized_line = line.strip()
            if normalized_line.lower() in {"primera vuelta", "segunda vuelta"}:
                stage = normalized_line.title()
                continue

            round_match = re.match(r"Jornada\s+(\d+)\s+\(([^)]+)\)", normalized_line)
            if round_match:
                current_round = int(round_match.group(1))
                current_date = round_match.group(2).strip()
                buffer = ""
                continue

            if not normalized_line:
                continue

            buffer = f"{buffer} {normalized_line}".strip()
            if " - " not in buffer or current_round is None or current_date is None:
                continue

            home_team, away_team = [part.strip() for part in buffer.split(" - ", 1)]
            buffer = ""

            if not home_team or not away_team:
                continue

            upper_home = home_team.upper()
            upper_away = away_team.upper()
            if self.TEAM_NAME not in {upper_home, upper_away}:
                continue

            venue = "home" if upper_home == self.TEAM_NAME else "away"
            opponent = away_team if venue == "home" else home_team

            fixtures.append(
                RealTajoFixture(
                    stage=stage,
                    round_number=current_round,
                    date=current_date,
                    opponent=opponent,
                    venue=venue,
                    home_team=home_team,
                    away_team=away_team,
                )
            )

        return fixtures

    def _extract_team_details(self, document: ParsedDocument) -> TeamDetails:
        lines = list(self._iter_lines(document))
        target_index = self._find_detail_index(lines)
        if target_index is None:
            raise ValueError("Unable to locate Real Tajo team details in the document.")

        block_end = self._find_block_end(lines, target_index)
        block = lines[target_index:block_end]

        contact = self._extract_after_label(block[0], "Contacto:")

        address = next(
            (
                line
                for line in block[1:]
                if not line.startswith("Teléfono:") and "Equipación" not in line and ":" not in line
            ),
            None,
        )

        phone_line = next((line for line in block if line.startswith("Teléfono:")), None)
        phone = self._extract_after_label(phone_line, "Teléfono:") if phone_line else None

        primary_kit = self._extract_kit(block, "Primera Equipación")
        secondary_kit = self._extract_kit(block, "2ª Equipación")

        return TeamDetails(
            contact=contact or None,
            address=address or None,
            phone=phone or None,
            primary_kit=primary_kit,
            secondary_kit=secondary_kit,
        )

    def _extract_kit(self, block: List[str], heading: str) -> KitDetails:
        try:
            heading_index = block.index(heading)
        except ValueError:
            return KitDetails()

        type_line = block[heading_index + 1] if heading_index + 1 < len(block) else ""
        color_line = block[heading_index + 2] if heading_index + 2 < len(block) else ""
        type_values = self._parse_colon_separated_values(type_line)
        color_values = self._parse_colon_separated_values(color_line)
        return KitDetails(
            shirt_type=type_values.get("Tipo Camiseta"),
            shorts_type=type_values.get("Tipo Pantalón"),
            socks_type=type_values.get("Tipo Medias"),
            shirt=color_values.get("Camiseta"),
            shorts=color_values.get("Pantalón"),
            socks=color_values.get("Medias"),
        )

    def _find_block_end(self, lines: List[str], start_index: int) -> int:
        for index in range(start_index + 1, len(lines)):
            line = lines[index]
            if "Contacto:" in line and self.TEAM_NAME not in line.upper():
                return index
        return len(lines)

    def _parse_colon_separated_values(self, line: str) -> dict[str, str | None]:
        pattern = r"([^:]+):\s*([^:]+?)(?=\s+[^:]+:|$)"
        return {match.group(1).strip(): match.group(2).strip() or None for match in re.finditer(pattern, line)}

    def _extract_after_label(self, text: str | None, label: str) -> str | None:
        if text is None or label not in text:
            return None
        return text.split(label, 1)[1].strip() or None

    def _find_detail_index(self, lines: List[str]) -> int | None:
        for index, line in enumerate(lines):
            if line.upper().startswith(f"{self.TEAM_NAME} CONTACTO:") or "REAL TAJO Contacto:" in line:
                return index
        return None

    def _iter_lines(self, document: ParsedDocument) -> Iterable[str]:
        for page in document.pages:
            for line in page.content:
                yield line
