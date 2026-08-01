"""Discover convertible files from user-selected paths."""

from __future__ import annotations

from pathlib import Path

from app.config import SUPPORTED_EXTENSIONS
from app.models import FileJob


def scan_paths(paths: list[Path], *, recursive: bool = True) -> list[FileJob]:
    """
    Collect convertible files (.docx / .xlsx / .pdf / images) from files and folders.

    Relative path is computed against the nearest selected root:
    - for a file selection: relative name only
    - for a folder selection: path relative to that folder
    """
    jobs: list[FileJob] = []
    seen: set[Path] = set()

    for raw in paths:
        path = Path(raw).resolve()
        if not path.exists():
            continue

        if path.is_file():
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and _is_convertible(path):
                key = path
                if key not in seen:
                    seen.add(key)
                    jobs.append(FileJob(source=path, relative=Path(path.name)))
            continue

        if path.is_dir():
            pattern_iter = path.rglob("*") if recursive else path.glob("*")
            for candidate in pattern_iter:
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                if not _is_convertible(candidate):
                    continue
                # Skip Office lock/temp files.
                if candidate.name.startswith("~$"):
                    continue
                key = candidate.resolve()
                if key in seen:
                    continue
                seen.add(key)
                try:
                    rel = candidate.resolve().relative_to(path)
                except ValueError:
                    rel = Path(candidate.name)
                jobs.append(FileJob(source=key, relative=rel))

    jobs.sort(key=lambda j: str(j.source).lower())
    return jobs


def _is_convertible(path: Path) -> bool:
    # Skip macro-enabled / template variants not in SUPPORTED_EXTENSIONS by design.
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
