"""Shared data models for conversion jobs and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


ImageMode = Literal["skip", "placeholder"]


@dataclass
class ConvertOptions:
    """User-facing conversion options (GUI + CLI share this)."""

    preserve_structure: bool = True
    yaml_frontmatter: bool = True
    collapse_blank_lines: bool = True
    skip_empty_excel_rows: bool = True
    excel_one_file_per_sheet: bool = False
    image_mode: ImageMode = "placeholder"
    overwrite: bool = True


@dataclass
class FileJob:
    """Single source file to convert."""

    source: Path
    # Relative path from the scan root (for preserving folder structure).
    relative: Path


@dataclass
class ConvertResult:
    """Outcome of converting one source file."""

    source: Path
    outputs: list[Path] = field(default_factory=list)
    ok: bool = True
    error: str | None = None
    bytes_in: int = 0
    bytes_out: int = 0

    @property
    def compression_ratio(self) -> float | None:
        if self.bytes_in <= 0:
            return None
        return self.bytes_out / self.bytes_in


@dataclass
class BatchSummary:
    """Aggregate stats after a batch run."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    results: list[ConvertResult] = field(default_factory=list)

    @property
    def saved_bytes(self) -> int:
        return max(0, self.bytes_in - self.bytes_out)

    @property
    def compression_percent(self) -> float | None:
        if self.bytes_in <= 0:
            return None
        return (1.0 - self.bytes_out / self.bytes_in) * 100.0
