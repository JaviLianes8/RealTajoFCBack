# RealTajoFCBack

Backend application for processing the Real Tajo club data.

## Requirements

- Python 3.11+

## Installation

```bash
pip install -r requirements.txt
```

## Running the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

The server will be available from external networks (if permitted) on port `8765`.

## Automated scraping (ffmadrid.es → back)

The `scripts/run_scraper.py` CLI logs into the federation portal, scrapes the
classification, latest matchday, top scorers and Real Tajo calendar, and pushes
each JSON payload to the back's `PUT/POST` endpoints. The GitHub Actions
workflow `.github/workflows/scrape.yml` runs it every 12 hours.

### Required GitHub repository secrets

| Secret | Value |
|---|---|
| `FFMADRID_USER` | Club login at aranjuez.ffmadrid.es |
| `FFMADRID_PASS` | Password for the above |
| `BACK_API_KEY` | Shared secret sent as `X-API-Key` header to the back |

### Required env vars in production (Azure App Service)

| Variable | Purpose |
|---|---|
| `BACK_API_KEY` | Same value as the GitHub secret. When unset the back logs a warning and **leaves mutating endpoints unprotected**. |

### Federation codes (hardcoded in the workflow)

The current season uses:

- `FFMADRID_COD_PRIMARIA=1000128`
- `FFMADRID_COD_COMPETICION=1009587`
- `FFMADRID_COD_GRUPO=1009597`
- `FFMADRID_COD_TEMPORADA=21` ← change each new season

When the season changes, edit those values in `.github/workflows/scrape.yml`.

### Running the scraper locally

Copy `.env.example` to `.env` and fill it in. Then:

```bash
# Dry run: scrape only, do not push to back
DRY_RUN=1 python scripts/run_scraper.py

# Real run: scrape + push
python scripts/run_scraper.py
```

If your network injects a self-signed root certificate (corporate proxy), use
`POC_INSECURE_TLS=1` to skip TLS verification (local only, never in CI).

### Triggering the workflow manually

From the GitHub Actions tab, open "Scrape ffmadrid and push to back" and click
**Run workflow**. Logs show how many teams, fixtures, scorers and matches were
extracted and the HTTP response from each back endpoint.

## Available endpoints

All endpoints are exposed under the API prefix configured via `API_PREFIX` (defaults to `/api`). Upload endpoints now accept JSON payloads that must match the structures produced previously from PDF/Excel conversions.

- `PUT /classification`: store the latest classification table.
- `GET /classification`: retrieve the most recently stored classification table.
- `PUT /schedule`: store the latest competition schedule.
- `GET /schedule`: retrieve the most recently stored competition schedule.
- `PUT /real-tajo/calendar`: store the latest Real Tajo calendar.
- `GET /real-tajo/calendar`: retrieve the most recently stored Real Tajo calendar.
- `PUT /top-scorers`: store the latest top scorers table.
- `GET /top-scorers`: retrieve the most recently stored top scorers table.
- `PUT /matchdays`: upload and parse a matchday PDF document.
- `POST /matchdays/last`: store a matchday JSON payload as the latest record.
- `GET /matchdays/last`: retrieve the latest stored matchday focusing on Real Tajo.

### JSON payload specifications

The following sections describe the exact JSON structures expected by each upload endpoint. Use the same field names and nesting as shown below.

#### `PUT /classification`

```json
{
  "metadata": {
    "headers": ["Clasificación Liga"],
    "columns": [
      {"key": "team", "label": "Equipos"},
      {"key": "points", "label": "Puntos"},
      {
        "key": "matches",
        "label": "Partidos",
        "children": [
          {"key": "played", "label": "J."},
          {"key": "wins", "label": "G."},
          {"key": "draws", "label": "E."},
          {"key": "losses", "label": "P."}
        ]
      },
      {
        "key": "goals",
        "label": "Goles",
        "children": [
          {"key": "for", "label": "F."},
          {"key": "against", "label": "C."}
        ]
      },
      {
        "key": "recent_form",
        "label": "Últimos",
        "children": [{"key": "points", "label": "Puntos"}]
      },
      {
        "key": "sanction",
        "label": "Sanción",
        "children": [{"key": "points", "label": "Puntos"}]
      }
    ]
  },
  "teams": [
    {
      "position": 1,
      "team": "REAL TAJO",
      "points": 42,
      "matches": {"played": 18, "wins": 14, "draws": 0, "losses": 4},
      "goals": {"for": 65, "against": 27},
      "recent_form": {"points": 12},
      "sanction": {"points": 0},
      "raw": "1 REAL TAJO 42 pts"
    }
  ],
  "last_match": {
    "matchday": 18,
    "date": "2024-02-18",
    "home_team": {"name": "REAL TAJO", "score": 3},
    "away_team": {"name": "RIVAL FC", "score": 1}
  }
}
```

#### `PUT /schedule`

```json
{
  "pages": [
    {
      "number": 1,
      "content": [
        "Jornada 1 - REAL TAJO vs RIVAL FC",
        "Jornada 2 - DESCANSA"
      ]
    },
    {
      "number": 2,
      "content": ["Jornada 18 - RIVAL FC vs REAL TAJO"]
    }
  ]
}
```

#### `PUT /real-tajo/calendar`

```json
{
  "competition": "Preferente Grupo 1",
  "season": "2023-2024",
  "matches": [
    {
      "stage": "Liga",
      "matchday": 1,
      "date": "2023-09-10",
      "opponent": "RIVAL FC",
      "is_home": true,
      "time": "18:00",
      "field": "Campo Municipal"
    }
  ],
  "team_info": {
    "name": "REAL TAJO",
    "contact_name": "Coordinador",
    "phone": "600000000",
    "address": "C/ Principal s/n",
    "first_kit": {
      "shirt": "Azul",
      "shorts": "Blanco",
      "socks": "Azul",
      "shirt_type": "Color sólido",
      "shorts_type": null,
      "socks_type": null
    },
    "second_kit": {
      "shirt": "Blanco",
      "shorts": "Azul",
      "socks": "Blanco",
      "shirt_type": null,
      "shorts_type": null,
      "socks_type": null
    }
  }
}
```

#### `PUT /top-scorers`

```json
{
  "metadata": {
    "title": "Goleadores",
    "competition": "Preferente Grupo 1",
    "category": "Senior",
    "season": "2023-2024",
    "columns": [
      {"key": "position", "label": "#"},
      {"key": "player", "label": "Jugador"},
      {"key": "team", "label": "Equipo"},
      {"key": "group", "label": "Grupo"},
      {"key": "matches_played", "label": "Partidos"},
      {"key": "goals", "label": "Goles"},
      {"key": "goals_per_match", "label": "Goles/Partido"}
    ]
  },
  "rows": [
    {
      "position": 1,
      "player": "Juan Pérez",
      "team": "REAL TAJO",
      "group": "A",
      "matches_played": 18,
      "goals": {"total": 22, "details": "15+7", "penalties": 3},
      "goals_per_match": 1.22,
      "raw": ["Juan Pérez - 22 goles"]
    }
  ]
}
```

All properties are optional unless the example demonstrates otherwise, but the object hierarchy and field names must match exactly. Dates must be formatted as `YYYY-MM-DD` and boolean fields should be standard JSON booleans.

#### `POST /matchdays/last`

```json
{
  "matchdayNumber": 3,
  "fixtures": [
    {
      "homeTeam": "LA VESPA",
      "awayTeam": "REAL TAJO",
      "homeScore": 0,
      "awayScore": 1,
      "isBye": false,
      "date": "2025-10-25",
      "time": "17:00"
    }
  ]
}
```

Provide the same structure produced by the existing PDF processing flow. The service stores the payload as-is and exposes it immediately through `GET /matchdays/last`.
