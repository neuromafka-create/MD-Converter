"""Bundled tessdata (rus+eng) must drive OCR, not system eng-only install."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from app.utils.ocr import (
    bundled_tessdata_dir,
    ensure_langs_available,
    list_trained_langs,
    ocr_image_to_text,
    resolve_tessdata_dir,
)


def test_bundled_tessdata_has_rus_and_eng():
    directory = bundled_tessdata_dir()
    assert directory is not None, "Run .\\scripts\\download_tessdata.ps1"
    langs = {x.lower() for x in list_trained_langs(directory)}
    assert "rus" in langs
    assert "eng" in langs
    assert resolve_tessdata_dir() == directory


def test_ensure_langs_reports_missing(tmp_path: Path):
    # Empty dir → rus missing
    try:
        ensure_langs_available("rus+eng", tmp_path)
        raised = False
    except Exception as exc:
        raised = True
        assert "rus" in str(exc).lower() or "нет языков" in str(exc).lower()
    assert raised


def test_russian_ocr_reads_cyrillic():
    """Regression: eng-only tessdata turned Cyrillic into Latin garbage."""
    if not bundled_tessdata_dir():
        return  # skip if models not present in CI without download

    # Large high-contrast Russian line (default font is weak; use Arial if present).
    img = Image.new("RGB", (900, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    phrase = "создай промпт для Midjourney"
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
        except OSError:
            font = ImageFont.load_default()
    draw.text((20, 40), phrase, fill=(0, 0, 0), font=font)

    text = ocr_image_to_text(img, lang="rus+eng", psm=6)
    lowered = text.lower().replace("ё", "е")
    # Must contain real Cyrillic, not only Latin look-alikes.
    assert any("\u0400" <= ch <= "\u04FF" for ch in text), f"no Cyrillic in: {text!r}"
    # Key tokens from the phrase (OCR may vary slightly on synthetic fonts).
    assert "midjourney" in lowered or "созда" in lowered or "промпт" in lowered, text
