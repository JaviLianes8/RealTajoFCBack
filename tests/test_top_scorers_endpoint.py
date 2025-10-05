"""End-to-end tests for the top scorers HTTP endpoints."""
from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import create_app


def _build_workbook(rows: list[list[object]]) -> bytes:
    """Return Excel workbook bytes populated with ``rows``."""

    workbook = Workbook()
    worksheet = workbook.active
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _create_test_client(monkeypatch, tmp_path) -> TestClient:
    """Return a test client bound to a temporary storage directory."""

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    return TestClient(create_app())


def test_upload_top_scorers_rejects_non_excel_content_type(monkeypatch, tmp_path) -> None:
    """Uploading a file with a non-Excel MIME type should return ``400``."""

    client = _create_test_client(monkeypatch, tmp_path)

    response = client.put(
        "/api/v1/top-scorers",
        files={
            "file": (
                "Goleadores.xlsx",
                b"dummy",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file must be an Excel (.xlsx) file."


def test_upload_top_scorers_rejects_invalid_excel_file(monkeypatch, tmp_path) -> None:
    """Uploading bytes that are not a workbook must yield ``422``."""

    client = _create_test_client(monkeypatch, tmp_path)

    response = client.put(
        "/api/v1/top-scorers",
        files={
            "file": (
                "Goleadores.xlsx",
                b"not-an-excel-file",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The provided file is not a valid Excel workbook."


def test_upload_and_retrieve_top_scorers_table(monkeypatch, tmp_path) -> None:
    """A valid workbook upload should persist and be retrievable."""

    client = _create_test_client(monkeypatch, tmp_path)

    workbook_bytes = _build_workbook(
        [
            ["", "", "LIGA AFICIONADOS F-11, 2ª AFICIONADOS F-11"],
            ["", "Temporada 2025-2026"],
            [],
            ["Jugador", "Equipo", "Grupo", "Partidos Jugados", "Goles", "Goles partido"],
            [
                "ARRIAGA MARTINEZ, MANUEL",
                "NEW COTTON MEKASO MCS",
                "2ª AFICIONADOS F-11",
                3,
                "5 (2 de penalti)",
                "1,6667",
            ],
        ]
    )

    response = client.put(
        "/api/v1/top-scorers",
        files={
            "file": (
                "Goleadores.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["Location"] == "/api/v1/top-scorers"

    payload = response.json()
    assert payload["metadata"]["season"] == "2025-2026"
    assert payload["metadata"]["competition"] == "LIGA AFICIONADOS F-11"
    assert payload["rows"][0]["player"] == "ARRIAGA MARTINEZ, MANUEL"
    assert payload["rows"][0]["goals"]["penalties"] == 2

    retrieval = client.get("/api/v1/top-scorers")

    assert retrieval.status_code == 200
    assert retrieval.json() == payload
