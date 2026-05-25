"""CLI orchestrator: scrape ffmadrid.es and push the JSON payloads to the back.

Environment variables (read from process env first, ``.env`` next to this file
as a fallback)::

    FFMADRID_USER, FFMADRID_PASS               - federation credentials
    FFMADRID_BASE_URL                          - https://aranjuez.ffmadrid.es
    FFMADRID_COD_PRIMARIA                      - club code
    FFMADRID_COD_COMPETICION
    FFMADRID_COD_GRUPO
    FFMADRID_COD_TEMPORADA
    BACK_BASE_URL                              - https://...azurewebsites.net (no trailing slash)
    BACK_API_PREFIX                            - defaults to /api/v1
    BACK_API_KEY                               - sent as X-API-Key header
    DRY_RUN                                    - "1" to skip HTTP POSTs to the back
    POC_INSECURE_TLS                           - "1" to skip TLS verification (corp proxy)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import requests
import urllib3

from app.infrastructure.scrapers.calendar_scraper import parse_calendar
from app.infrastructure.scrapers.classification_scraper import parse_classification
from app.infrastructure.scrapers.ffmadrid_session import FfmadridCredentials, FfmadridSession
from app.infrastructure.scrapers.matchday_scraper import parse_matchday
from app.infrastructure.scrapers.top_scorers_scraper import parse_top_scorers


DEFAULT_BACK_BASE_URL = "https://realtajoback-b8a4dxbxdkhtgham.westeurope-01.azurewebsites.net"
DEFAULT_BACK_API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class Config:
    ff_user: str
    ff_pass: str
    ff_base_url: str
    cod_primaria: str
    cod_competicion: str
    cod_grupo: str
    cod_temporada: str
    back_base_url: str
    back_api_prefix: str
    back_api_key: str | None
    dry_run: bool
    verify_tls: bool


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    log = logging.getLogger("scraper")
    config = _load_config()
    if not config.verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = FfmadridSession(
        base_url=config.ff_base_url,
        credentials=FfmadridCredentials(config.ff_user, config.ff_pass),
        verify_tls=config.verify_tls,
    )

    classification_url = (
        f"{config.ff_base_url.rstrip('/')}/nfg/NPcd/NFG_VisClasificacion"
        f"?cod_primaria={config.cod_primaria}"
        f"&codcompeticion={config.cod_competicion}"
        f"&codgrupo={config.cod_grupo}"
    )
    top_scorers_url = (
        f"{config.ff_base_url.rstrip('/')}/nfg/NPcd/NFG_CMP_Goleadores"
        f"?cod_primaria={config.cod_primaria}"
        f"&codcompeticion={config.cod_competicion}"
        f"&codgrupo={config.cod_grupo}"
    )
    calendar_url = (
        f"{config.ff_base_url.rstrip('/')}/nfg/NPcd/NFG_VisCalendario_Vis"
        f"?cod_primaria={config.cod_primaria}"
        f"&codgrupo={config.cod_grupo}"
        f"&codcompeticion={config.cod_competicion}"
        f"&codtemporada={config.cod_temporada}"
        f"&codjornada=&cod_agrupacion=&CDetalle=1"
    )

    log.info("Fetching classification page")
    classification_html = session.get_html(classification_url)
    classification_payload = parse_classification(classification_html)
    log.info(
        "Classification: %d teams, last matchday=%s",
        len(classification_payload["teams"]),
        (classification_payload.get("last_match") or {}).get("matchday"),
    )

    matchday_payload: dict[str, Any] | None = None
    last_match = classification_payload.get("last_match")
    if last_match and last_match.get("matchday"):
        matchday_url = (
            f"{config.ff_base_url.rstrip('/')}/nfg/NPcd/NFG_CmpJornada"
            f"?cod_primaria={config.cod_primaria}"
            f"&CodCompeticion={config.cod_competicion}"
            f"&CodGrupo={config.cod_grupo}"
            f"&CodTemporada={config.cod_temporada}"
            f"&CodJornada={last_match['matchday']}"
        )
        log.info("Fetching matchday page (J%s)", last_match["matchday"])
        matchday_html = session.get_html(matchday_url)
        matchday_payload = parse_matchday(matchday_html)
        log.info("Matchday: %d fixtures", len(matchday_payload["fixtures"]))

    log.info("Fetching top scorers page")
    top_scorers_html = session.get_html(top_scorers_url)
    top_scorers_payload = parse_top_scorers(top_scorers_html)
    log.info("Top scorers: %d rows", len(top_scorers_payload["rows"]))

    log.info("Fetching calendar page")
    calendar_html = session.get_html(calendar_url)
    calendar_payload = parse_calendar(calendar_html)
    log.info("Calendar: %d matches", len(calendar_payload["matches"]))

    if config.dry_run:
        log.info("DRY_RUN=1, not posting to back. Payload sizes:")
        log.info("  classification: %d chars", len(json.dumps(classification_payload)))
        if matchday_payload is not None:
            log.info("  matchday:       %d chars", len(json.dumps(matchday_payload)))
        log.info("  top_scorers:    %d chars", len(json.dumps(top_scorers_payload)))
        log.info("  calendar:       %d chars", len(json.dumps(calendar_payload)))
        return 0

    http_client = _build_http_client(config)

    tasks: list[tuple[str, str, str, dict[str, Any]]] = [
        ("PUT", "/classification", "classification", classification_payload),
        ("PUT", "/top-scorers", "top_scorers", top_scorers_payload),
        ("PUT", "/real-tajo/calendar", "calendar", calendar_payload),
    ]
    if matchday_payload is not None:
        tasks.append(("POST", "/matchdays/last", "matchday", matchday_payload))

    failures = 0
    for method, path, label, payload in tasks:
        full_url = f"{config.back_base_url.rstrip('/')}{config.back_api_prefix}{path}"
        try:
            response = http_client.request(method, full_url, json=payload, timeout=30)
        except requests.RequestException as error:
            log.error("[%s] network error: %s", label, error)
            failures += 1
            continue
        if response.status_code >= 400:
            log.error(
                "[%s] %s %s -> %s: %s",
                label,
                method,
                path,
                response.status_code,
                response.text[:200],
            )
            failures += 1
        else:
            log.info("[%s] %s %s -> %s OK", label, method, path, response.status_code)

    return 0 if failures == 0 else 1


def _build_http_client(config: Config) -> requests.Session:
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"
    if config.back_api_key:
        session.headers["X-API-Key"] = config.back_api_key
    session.verify = config.verify_tls
    return session


def _load_config() -> Config:
    env = _load_env_fallback()
    return Config(
        ff_user=_required(env, "FFMADRID_USER"),
        ff_pass=_required(env, "FFMADRID_PASS"),
        ff_base_url=_required(env, "FFMADRID_BASE_URL"),
        cod_primaria=_required(env, "FFMADRID_COD_PRIMARIA"),
        cod_competicion=_required(env, "FFMADRID_COD_COMPETICION"),
        cod_grupo=_required(env, "FFMADRID_COD_GRUPO"),
        cod_temporada=_required(env, "FFMADRID_COD_TEMPORADA"),
        back_base_url=env.get("BACK_BASE_URL") or DEFAULT_BACK_BASE_URL,
        back_api_prefix=env.get("BACK_API_PREFIX") or DEFAULT_BACK_API_PREFIX,
        back_api_key=env.get("BACK_API_KEY") or None,
        dry_run=_bool_flag(env, "DRY_RUN"),
        verify_tls=not _bool_flag(env, "POC_INSECURE_TLS"),
    )


def _load_env_fallback() -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key not in os.environ:
                env[key] = value.strip().strip('"').strip("'")
    return env


def _required(env: dict[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env variable: {name}")
    return value


def _bool_flag(env: dict[str, str], name: str) -> bool:
    return env.get(name, "").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    raise SystemExit(main())
