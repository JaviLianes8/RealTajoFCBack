"""Smoke test the calendar scraper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.infrastructure.scrapers.calendar_scraper import parse_calendar
from app.infrastructure.scrapers.ffmadrid_session import FfmadridCredentials, FfmadridSession
from smoke_classification import load_env  # type: ignore


def main() -> int:
    env = load_env(Path(__file__).resolve().parent.parent / ".env")
    session = FfmadridSession(
        base_url=env["FFMADRID_BASE_URL"],
        credentials=FfmadridCredentials(env["FFMADRID_USER"], env["FFMADRID_PASS"]),
        verify_tls=os.getenv("POC_INSECURE_TLS", "").lower() not in ("1", "true", "yes"),
    )
    base = env["FFMADRID_BASE_URL"].rstrip("/")
    url = (
        f"{base}/nfg/NPcd/NFG_VisCalendario_Vis"
        f"?cod_primaria={env['FFMADRID_COD_PRIMARIA']}"
        f"&codgrupo={env['FFMADRID_COD_GRUPO']}"
        f"&codcompeticion={env['FFMADRID_COD_COMPETICION']}"
        f"&codtemporada={env['FFMADRID_COD_TEMPORADA']}"
        f"&codjornada=&cod_agrupacion=&CDetalle=1"
    )
    html = session.get_html(url)
    result = parse_calendar(html)
    print(f"competition: {result['competition']}")
    print(f"season: {result['season']}")
    print(f"matches: {len(result['matches'])}")
    for m in result["matches"]:
        side = "(L)" if m["is_home"] else "(V)"
        print(
            f"  J{m['matchday']} {m['date']} {m['time'] or '--:--'} | "
            f"{side} {m['opponent']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
