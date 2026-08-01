"""OCR helpers and PDF auto-OCR behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image, ImageDraw, ImageFont

from app.converters.pdf_converter import PdfConverter
from app.models import ConvertOptions, FileJob
from app.utils.ocr import (
    OcrError,
    ocr_text_to_markdown,
    _normalize_ocr_text,
)


def test_normalize_ocr_text_collapses_blank_runs():
    raw = "Line one\n\n\n\nLine two\n"
    assert _normalize_ocr_text(raw) == "Line one\n\nLine two"


def test_ocr_text_to_markdown_lists_and_paragraphs():
    text = "Intro line\n\n• First item\n• Second item\n\n1. Step one\n2. Step two\n"
    md = ocr_text_to_markdown(text)
    assert "Intro line" in md
    assert "- First item" in md
    assert "- Second item" in md
    assert "1. Step one" in md
    assert "1. Step two" in md


def _make_text_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Digital PDF with a real text layer.", fontsize=12)
    doc.save(path)
    doc.close()


def _make_scan_like_pdf(path: Path, label: str = "SCANNED DOCUMENT TEXT") -> None:
    """PDF whose only content is a raster image (no text layer)."""
    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 160), label, fill=(0, 0, 0), font=font)

    img_path = path.with_suffix(".png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, filename=str(img_path))
    doc.save(path)
    doc.close()
    img_path.unlink(missing_ok=True)


def test_auto_ocr_skips_digital_pdf(tmp_path: Path):
    src = tmp_path / "digital.pdf"
    _make_text_pdf(src)
    job = FileJob(source=src, relative=Path("digital.pdf"))
    # Even if OCR is "available", digital pages must not call it.
    with patch("app.converters.pdf_converter.is_ocr_available", return_value=True), patch(
        "app.converters.pdf_converter.ocr_pixmap_to_text"
    ) as ocr_mock:
        result = PdfConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="auto")
        )
    assert result.ok, result.error
    ocr_mock.assert_not_called()
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "Digital PDF" in md
    assert "ocr_pages" not in md


def test_auto_ocr_on_scan_without_tesseract_errors(tmp_path: Path):
    src = tmp_path / "scan.pdf"
    _make_scan_like_pdf(src)
    job = FileJob(source=src, relative=Path("scan.pdf"))
    with patch("app.converters.pdf_converter.is_ocr_available", return_value=False):
        result = PdfConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="auto")
        )
    assert not result.ok
    assert result.error
    assert "Tesseract" in result.error


def test_ocr_off_on_scan_yields_empty_or_placeholder(tmp_path: Path):
    src = tmp_path / "scan.pdf"
    _make_scan_like_pdf(src)
    job = FileJob(source=src, relative=Path("scan.pdf"))
    result = PdfConverter().convert(
        job,
        tmp_path / "out",
        ConvertOptions(ocr_mode="off", image_mode="skip"),
    )
    assert result.ok, result.error
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "No extractable text" in md or md.strip().endswith("# scan")


def test_force_ocr_uses_engine(tmp_path: Path):
    src = tmp_path / "digital.pdf"
    _make_text_pdf(src)
    job = FileJob(source=src, relative=Path("digital.pdf"))

    def fake_ocr(pix, *, lang: str = "rus+eng") -> str:
        return "OCR FORCED TEXT FROM ENGINE"

    with patch("app.converters.pdf_converter.is_ocr_available", return_value=True), patch(
        "app.converters.pdf_converter.ocr_pixmap_to_text", side_effect=fake_ocr
    ):
        result = PdfConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="force", ocr_lang="eng")
        )
    assert result.ok, result.error
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "OCR FORCED TEXT FROM ENGINE" in md
    assert "ocr_pages: 1" in md
    assert 'ocr_lang: "eng"' in md or "ocr_lang: eng" in md


def test_ocr_error_message_propagates(tmp_path: Path):
    src = tmp_path / "scan.pdf"
    _make_scan_like_pdf(src)
    job = FileJob(source=src, relative=Path("scan.pdf"))
    with patch("app.converters.pdf_converter.is_ocr_available", return_value=True), patch(
        "app.converters.pdf_converter.ocr_pixmap_to_text",
        side_effect=OcrError("bad language pack"),
    ):
        result = PdfConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="auto")
        )
    assert not result.ok
    assert "bad language pack" in (result.error or "")
