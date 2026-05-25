"""Smoke test the matchday scraper module against the live federation site."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.infrastructure.scrapers.classification_scraper import parse_classification
from app.infrastructure.scrapers.ffmadrid_session import FfmadridCredentials, FfmadridSession
from app.infrastructure.scrapers.matchday_scraper import parse_matchday


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    env = load_env(Path(__file__).resolve().parent.parent / ".env")
    session = FfmadridSession(
        base_url=env["FFMADRID_BASE_URL"],
        credentials=FfmadridCredentials(env["FFMADRID_USER"], env["FFMADRID_PASS"]),
        verify_tls=os.getenv("POC_INSECURE_TLS", "").lower() not in ("1", "true", "yes"),
    )
    classif_url = (
        f"{env['FFMADRID_BASE_URL'].rstrip('/')}/nfg/NPcd/NFG_VisClasificacion"
        f"?cod_primaria={env['FFMADRID_COD_PRIMARIA']}"
        f"&codcompeticion={env['FFMADRID_COD_COMPETICION']}"
        f"&codgrupo={env['FFMADRID_COD_GRUPO']}"
    )
    classif_html = session.get_html(classif_url)
    classif = parse_classification(classif_html)
    matchday_number = classif["last_match"]["matchday"] if classif["last_match"] else 0
    print(f"Detected matchday from classification: {matchday_number}")

    matchday_url = (
        f"{env['FFMADRID_BASE_URL'].rstrip('/')}/nfg/NPcd/NFG_CmpJornada"
        f"?cod_primaria={env['FFMADRID_COD_PRIMARIA']}"
        f"&CodCompeticion={env['FFMADRID_COD_COMPETICION']}"
        f"&CodGrupo={env['FFMADRID_COD_GRUPO']}"
        f"&CodTemporada={env['FFMADRID_COD_TEMPORADA']}"
        f"&CodJornada={matchday_number}"
    )
    matchday_html = session.get_html(matchday_url)
    matchday = parse_matchday(matchday_html)
    print(json.dumps(matchday, indent=2, ensure_ascii=False))
    print(f"Fixtures: {len(matchday['fixtures'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
