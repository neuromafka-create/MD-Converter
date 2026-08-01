"""Image → Markdown OCR converter tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from app.converters.image_converter import ImageConverter
from app.core.scanner import scan_paths
from app.models import ConvertOptions, FileJob
from app.utils.ocr import load_image_for_ocr


def _write_png(path: Path, text: str = "Hello webinar") -> None:
    img = Image.new("RGB", (640, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill=(0, 0, 0), font=font)
    img.save(path, format="PNG")


def _write_jpg(path: Path) -> None:
    img = Image.new("RGB", (400, 120), color=(240, 240, 240))
    ImageDraw.Draw(img).text((10, 50), "JPG slide", fill=(0, 0, 0))
    img.save(path, format="JPEG", quality=90)


def test_scanner_picks_images(tmp_path: Path):
    root = tmp_path / "shots"
    root.mkdir()
    _write_png(root / "slide1.png")
    _write_jpg(root / "slide2.jpg")
    (root / "notes.txt").write_text("skip", encoding="utf-8")

    jobs = scan_paths([root], recursive=True)
    names = {j.source.name for j in jobs}
    assert names == {"slide1.png", "slide2.jpg"}


def test_image_conversion_with_mocked_ocr(tmp_path: Path):
    src = tmp_path / "webinar_slide.png"
    _write_png(src, "Agenda item one")
    job = FileJob(source=src, relative=Path("webinar_slide.png"))

    def fake_ocr(path, *, lang="rus+eng", max_side=None, psm=3):
        return (
            "Повестка вебинара\n\n• Введение\n• Практика\n",
            {"width": 640, "height": 200, "format": "png"},
        )

    with patch("app.converters.image_converter.ocr_image_file", side_effect=fake_ocr):
        result = ImageConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="auto")
        )

    assert result.ok, result.error
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "type: png" in md
    assert "ocr: true" in md
    assert "ocr_lang:" in md
    assert "width: 640" in md
    assert "Повестка вебинара" in md
    assert "- Введение" in md
    assert "- Практика" in md


def test_image_ocr_off_refused(tmp_path: Path):
    src = tmp_path / "x.png"
    _write_png(src)
    job = FileJob(source=src, relative=Path("x.png"))
    result = ImageConverter().convert(
        job, tmp_path / "out", ConvertOptions(ocr_mode="off")
    )
    assert not result.ok
    assert "OCR" in (result.error or "")


def test_image_missing_tesseract(tmp_path: Path):
    src = tmp_path / "x.png"
    _write_png(src)
    job = FileJob(source=src, relative=Path("x.png"))
    with patch("app.utils.ocr.is_ocr_available", return_value=False):
        result = ImageConverter().convert(
            job, tmp_path / "out", ConvertOptions(ocr_mode="auto")
        )
    assert not result.ok
    assert "Tesseract" in (result.error or "")


def test_load_image_downscales(tmp_path: Path):
    src = tmp_path / "huge.png"
    Image.new("RGB", (4000, 2000), color=(255, 255, 255)).save(src)
    img, meta = load_image_for_ocr(src, max_side=1000)
    assert max(img.size) <= 1000
    assert meta["original_width"] == 4000
    assert meta["width"] <= 1000


def test_jpg_type_in_frontmatter(tmp_path: Path):
    src = tmp_path / "photo.jpeg"
    _write_jpg(src)
    job = FileJob(source=src, relative=Path("photo.jpeg"))

    with patch(
        "app.converters.image_converter.ocr_image_file",
        return_value=("Line from photo", {"width": 400, "height": 120, "format": "jpeg"}),
    ):
        result = ImageConverter().convert(job, tmp_path / "out", ConvertOptions())
    assert result.ok, result.error
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "type: jpg" in md
    assert "Line from photo" in md
