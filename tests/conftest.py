"""Test configuration ensuring the application package is importable."""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Add the project's ``src`` directory to ``sys.path`` when missing."""

    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


_ensure_src_on_path()
