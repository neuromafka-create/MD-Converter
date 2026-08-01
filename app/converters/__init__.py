from __future__ import annotations

from pathlib import Path

from app.config import IMAGE_EXTENSIONS
from app.converters.base import BaseConverter
from app.converters.docx_converter import DocxConverter
from app.converters.image_converter import ImageConverter
from app.converters.pdf_converter import PdfConverter
from app.converters.xlsx_converter import XlsxConverter
from app.models import ConvertOptions, ConvertResult, FileJob


def get_converter(path: Path) -> BaseConverter:
    ext = path.suffix.lower()
    if ext == ".docx":
        return DocxConverter()
    if ext == ".xlsx":
        return XlsxConverter()
    if ext == ".pdf":
        return PdfConverter()
    if ext in IMAGE_EXTENSIONS:
        return ImageConverter()
    raise ValueError(f"Unsupported file type: {ext}")


def convert_job(
    job: FileJob,
    output_dir: Path,
    options: ConvertOptions,
) -> ConvertResult:
    """Dispatch a single job to the right converter."""
    try:
        converter = get_converter(job.source)
        return converter.convert(job, output_dir, options)
    except Exception as exc:  # noqa: BLE001 — surface any converter failure as result
        bytes_in = 0
        try:
            bytes_in = job.source.stat().st_size
        except OSError:
            pass
        return ConvertResult(
            source=job.source,
            outputs=[],
            ok=False,
            error=str(exc),
            bytes_in=bytes_in,
            bytes_out=0,
        )


__all__ = [
    "BaseConverter",
    "DocxConverter",
    "XlsxConverter",
    "PdfConverter",
    "ImageConverter",
    "get_converter",
    "convert_job",
]
