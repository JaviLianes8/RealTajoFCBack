"""End-to-end smoke test of the classification scraper module."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.infrastructure.scrapers.classification_scraper import parse_classification
from app.infrastructure.scrapers.ffmadrid_session import FfmadridCredentials, FfmadridSession


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
    url = (
        f"{env['FFMADRID_BASE_URL'].rstrip('/')}/nfg/NPcd/NFG_VisClasificacion"
        f"?cod_primaria={env['FFMADRID_COD_PRIMARIA']}"
        f"&codcompeticion={env['FFMADRID_COD_COMPETICION']}"
        f"&codgrupo={env['FFMADRID_COD_GRUPO']}"
    )
    html = session.get_html(url)
    payload = parse_classification(html)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    print(f"Teams: {len(payload['teams'])}, last_match: {payload['last_match']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
