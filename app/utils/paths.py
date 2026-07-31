"""Path helpers for safe output names and structure mirroring."""

from __future__ import annotations

import re
from pathlib import Path

from app.models import ConvertOptions

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_stem(name: str, max_len: int = 120) -> str:
    """Sanitize a filename stem for Windows."""
    stem = Path(name).stem if name else "document"
    stem = _INVALID_CHARS.sub("_", stem).strip(" .")
    if not stem:
        stem = "document"
    if len(stem) > max_len:
        stem = stem[:max_len].rstrip(" .")
    return stem


def ensure_unique_path(path: Path) -> Path:
    """If path exists, append _1, _2, ... before the suffix."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def output_path_for(
    job_source: Path,
    job_relative: Path,
    output_dir: Path,
    options: ConvertOptions,
    *,
    suffix: str = "",
    ext: str = ".md",
) -> Path:
    """
    Compute destination .md path.

    suffix is appended to the stem (e.g. sheet name: "_Sheet1").
    """
    stem = safe_stem(job_source.name)
    if suffix:
        stem = f"{stem}_{safe_stem(suffix)}"

    if options.preserve_structure and job_relative.parent != Path("."):
        # Keep original folder names, scrub only Windows-invalid characters.
        rel_parent = Path(*[_scrub_part(p) for p in job_relative.parent.parts])
        dest_dir = output_dir / rel_parent
    else:
        dest_dir = output_dir

    dest = dest_dir / f"{stem}{ext}"
    if not options.overwrite:
        dest = ensure_unique_path(dest)
    return dest


def _scrub_part(part: str) -> str:
    cleaned = _INVALID_CHARS.sub("_", part).strip(" .")
    return cleaned or "_"
