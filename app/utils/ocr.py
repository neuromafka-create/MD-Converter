"""OCR helpers for scanned PDFs (Tesseract via pytesseract)."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

# Common Windows install locations (UB Mannheim builds, winget, chocolatey).
_WINDOWS_TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract",
)


class OcrError(RuntimeError):
    """Raised when OCR cannot run (missing engine, bad language, etc.)."""


@lru_cache(maxsize=1)
def find_tesseract() -> str | None:
    """
    Locate the Tesseract executable.

    Order: TESSDATA / TESSERACT_CMD env, PATH, common Windows paths.
    """
    for env_key in ("TESSERACT_CMD", "TESSERACT_PATH"):
        raw = os.environ.get(env_key, "").strip().strip('"')
        if raw:
            path = Path(raw)
            if path.is_file():
                return str(path)

    which = shutil.which("tesseract")
    if which:
        return which

    for candidate in _WINDOWS_TESSERACT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate

    return None


def is_ocr_available() -> bool:
    return find_tesseract() is not None


def configure_pytesseract() -> str:
    """Point pytesseract at a discovered binary. Returns the path used."""
    path = find_tesseract()
    if not path:
        raise OcrError(
            "Tesseract OCR не найден. Установите его, например:\n"
            "  winget install --id UB-Mannheim.TesseractOCR -e\n"
            "или задайте путь: set TESSERACT_CMD=C:\\…\\tesseract.exe"
        )
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = path
    return path


def ocr_image_to_text(
    image,
    *,
    lang: str = "rus+eng",
    psm: int = 3,
) -> str:
    """
    Run Tesseract on a PIL Image (or compatible object).

    ``psm=3`` — fully automatic page segmentation (good default for scans).
    """
    configure_pytesseract()
    import pytesseract

    config = f"--psm {psm}"
    try:
        text = pytesseract.image_to_string(image, lang=lang, config=config)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(str(exc)) from exc
    except pytesseract.TesseractError as exc:
        # Missing language packs often surface here.
        msg = str(exc)
        if "Failed loading language" in msg or "Error opening data file" in msg:
            raise OcrError(
                f"Не удалось загрузить языки OCR «{lang}». "
                "При установке Tesseract отметьте Russian + English, "
                "или укажите ocr_lang (например eng)."
            ) from exc
        raise OcrError(f"Tesseract error: {msg}") from exc

    return _normalize_ocr_text(text)


def ocr_pixmap_to_text(pix, *, lang: str = "rus+eng") -> str:
    """OCR a PyMuPDF Pixmap without writing temp files."""
    from io import BytesIO

    from PIL import Image

    # PNG round-trip is reliable across colorspaces (RGB/Gray/CMYK/alpha).
    img = Image.open(BytesIO(pix.tobytes("png")))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return ocr_image_to_text(img, lang=lang)


def _normalize_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    # Drop trailing empty lines; keep single blank as paragraph break.
    while lines and not lines[-1].strip():
        lines.pop()
    # Collapse runs of 3+ blanks to one blank line.
    out: list[str] = []
    blank_run = 0
    for ln in lines:
        if not ln.strip():
            blank_run += 1
            if blank_run <= 1:
                out.append("")
        else:
            blank_run = 0
            out.append(ln)
    return "\n".join(out).strip()


def ocr_text_to_markdown(text: str) -> str:
    """Light structure pass over OCR plain text (lists + paragraphs)."""
    import re

    if not text.strip():
        return ""

    bullet_re = re.compile(r"^[\u2022\u2023\u25E6\u2043\u2219•●○▪▫►\-–—]\s+")
    numbered_re = re.compile(r"^(\d{1,3})[.)]\s+")

    lines = text.split("\n")
    parts: list[str] = []
    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            parts.append(" ".join(para).strip())
            para = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_para()
            continue
        m_b = bullet_re.match(line)
        if m_b:
            flush_para()
            parts.append(f"- {line[m_b.end():].strip()}")
            continue
        m_n = numbered_re.match(line)
        if m_n:
            flush_para()
            parts.append(f"1. {line[m_n.end():].strip()}")
            continue
        para.append(line)

    flush_para()

    # Join consecutive list items without blank lines; paragraphs with blank.
    out: list[str] = []
    prev_list = False
    for chunk in parts:
        is_list = chunk.startswith(("- ", "1. "))
        if out:
            if is_list and prev_list:
                pass  # no blank between list items
            else:
                out.append("")
        out.append(chunk)
        prev_list = is_list

    return "\n".join(out).strip() + ("\n" if parts else "")
