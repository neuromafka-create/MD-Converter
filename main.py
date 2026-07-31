#!/usr/bin/env python3
"""MD-Converter entry point."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def main() -> int:
    _ensure_project_root_on_path()
    from app.gui import run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
