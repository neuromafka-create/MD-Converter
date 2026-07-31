"""Converter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models import ConvertOptions, ConvertResult, FileJob


class BaseConverter(ABC):
    @abstractmethod
    def convert(
        self,
        job: FileJob,
        output_dir: Path,
        options: ConvertOptions,
    ) -> ConvertResult:
        """Convert one source file into one or more Markdown outputs."""
