"""Command-line entry point for running the Document Processor API server."""
from __future__ import annotations

import sys
from pathlib import Path


def _add_project_root_to_path() -> None:
    """Make sure the project root is present on ``sys.path``."""

    project_root = Path(__file__).resolve().parents[2]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


def main() -> None:
    """Delegate to the root-level ``main`` module to start the server."""

    _add_project_root_to_path()
    from main import main as run_main

    run_main()


if __name__ == "__main__":
    main()
