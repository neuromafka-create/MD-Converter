"""Resolve paths to bundled assets (dev + PyInstaller frozen)."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repository / install root (folder containing main.py or the .exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    """
    Root for packaged data files.

    - Frozen (PyInstaller): sys._MEIPASS temp extract dir
    - Dev: project root
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return project_root()


def resource_path(*parts: str) -> Path:
    """Absolute path to a resource under the bundle (e.g. assets/logo.ico)."""
    return bundle_root().joinpath(*parts)
