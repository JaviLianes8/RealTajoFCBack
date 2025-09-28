"""ASGI entry point compatible with Azure App Service deployments."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI


def _ensure_src_on_path() -> None:
    """Add the ``src`` directory to ``sys.path`` when executing from the repo root."""

    current = Path(__file__).resolve().parent
    for candidate in (current, *current.parents):
        src_path = candidate / "src"
        if src_path.exists():
            src_path_str = str(src_path)
            if src_path_str not in sys.path:
                sys.path.insert(0, src_path_str)
            break


_ensure_src_on_path()

from app.main import app as _fastapi_app  # noqa: E402 (requires sys.path update)


def get_app() -> FastAPI:
    """Return the FastAPI application instance used by the ASGI server."""

    return _fastapi_app


app = get_app()

__all__ = ["app", "get_app"]
