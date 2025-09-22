"""Command-line entry point for running the FastAPI application."""
from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def _add_src_to_path() -> None:
    """Ensure the ``src`` directory is available on ``sys.path``."""

    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    src_dir_str = str(src_dir)
    if src_dir_str not in sys.path:
        sys.path.insert(0, src_dir_str)


def main() -> None:
    """Run the API server using Uvicorn."""

    _add_src_to_path()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8765, reload=False)


if __name__ == "__main__":
    main()
