"""OCR helpers for scanned PDFs and images (Tesseract via pytesseract)."""

from __future__ import annotations

import os
import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.resources import resource_path

# Common Windows install locations (UB Mannheim builds, winget, chocolatey).
_WINDOWS_TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract",
)

# Languages we ship under tessdata/ (see scripts/download_tessdata.ps1).
BUNDLED_OCR_LANGS = ("rus", "eng")
DEFAULT_OCR_LANG = "rus+eng"


class OcrError(RuntimeError):
    """Raised when OCR cannot run (missing engine, bad language, etc.)."""


@lru_cache(maxsize=1)
def find_tesseract() -> str | None:
    """
    Locate the Tesseract executable.

    Order: TESSERACT_CMD / TESSERACT_PATH env, PATH, common Windows paths.
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


@lru_cache(maxsize=1)
def bundled_tessdata_dir() -> Path | None:
    """
    Directory with project-shipped ``*.traineddata`` (rus + eng).

    Prefer this over the system tessdata so winget installs without Russian
    still recognize Cyrillic correctly.
    """
    candidates = [
        resource_path("tessdata"),
        # Dev fallback if resource_path layout differs
        Path(__file__).resolve().parent.parent.parent / "tessdata",
    ]
    for directory in candidates:
        if not directory.is_dir():
            continue
        if all((directory / f"{lang}.traineddata").is_file() for lang in BUNDLED_OCR_LANGS):
            return directory.resolve()
    return None


def resolve_tessdata_dir() -> Path:
    """
    Tessdata directory for OCR.

    1. Env ``TESSDATA_DIR`` (folder that contains *.traineddata)
    2. Bundled project tessdata (rus+eng)
    3. System tessdata next to tesseract.exe (often eng-only — last resort)
    """
    env_dir = os.environ.get("TESSDATA_DIR", "").strip().strip('"')
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p.resolve()

    bundled = bundled_tessdata_dir()
    if bundled is not None:
        return bundled

    tess = find_tesseract()
    if tess:
        system = Path(tess).resolve().parent / "tessdata"
        if system.is_dir():
            return system

    raise OcrError(
        "Не найдены языковые модели OCR (tessdata).\n"
        "Выполните: .\\scripts\\download_tessdata.ps1\n"
        "или положите rus.traineddata и eng.traineddata в папку tessdata/."
    )


def list_trained_langs(tessdata_dir: Path | None = None) -> list[str]:
    """Language codes present as ``*.traineddata`` (excluding osd)."""
    directory = tessdata_dir or resolve_tessdata_dir()
    langs: list[str] = []
    for path in sorted(directory.glob("*.traineddata")):
        code = path.stem
        if code.lower() == "osd":
            continue
        langs.append(code)
    return langs


def ensure_langs_available(lang: str, tessdata_dir: Path | None = None) -> None:
    """Raise OcrError if any language in a ``+``-joined string is missing."""
    directory = tessdata_dir or resolve_tessdata_dir()
    available = {x.lower() for x in list_trained_langs(directory)}
    missing = [part for part in lang.split("+") if part.strip() and part.strip().lower() not in available]
    if missing:
        have = ", ".join(sorted(available)) or "(пусто)"
        raise OcrError(
            f"В tessdata нет языков: {', '.join(missing)}.\n"
            f"Папка: {directory}\n"
            f"Доступно: {have}\n"
            "Запустите .\\scripts\\download_tessdata.ps1 (скачает rus+eng в проект)."
        )


def configure_pytesseract() -> str:
    """Point pytesseract at a discovered binary. Returns the path used."""
    path = find_tesseract()
    if not path:
        raise OcrError(
            "Tesseract OCR не найден. Установите движок (языки не обязательны — "
            "они вшиты в проект):\n"
            "  winget install --id UB-Mannheim.TesseractOCR -e\n"
            "или задайте путь: set TESSERACT_CMD=C:\\…\\tesseract.exe"
        )
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = path

    # Prefer bundled models over system tessdata (often eng-only after winget).
    # Tesseract 5: TESSDATA_PREFIX = directory that contains *.traineddata.
    # We rely on the env var (not --tessdata-dir in config) so paths with
    # spaces work; pytesseract splits config with shlex and breaks quoted paths.
    tessdata = resolve_tessdata_dir()
    os.environ["TESSDATA_PREFIX"] = str(tessdata.resolve())

    return path


def load_image_for_ocr(
    path: Path | str,
    *,
    max_side: int | None = None,
    min_side: int | None = None,
) -> tuple[Any, dict[str, Any]]:
    """
    Load an image file for OCR: EXIF orientation, RGB, optional up/downscale.

    Returns ``(pil_image, meta)`` where meta has width/height (after prep)
    and original dimensions when resized.
    """
    from PIL import Image, ImageOps

    from app.config import OCR_IMAGE_MAX_SIDE, OCR_IMAGE_MIN_SIDE

    if max_side is None:
        max_side = OCR_IMAGE_MAX_SIDE
    if min_side is None:
        min_side = OCR_IMAGE_MIN_SIDE

    path = Path(path)
    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise OcrError(f"Не удалось открыть изображение: {exc}") from exc

    img = ImageOps.exif_transpose(img)
    orig_w, orig_h = img.size

    if img.mode not in ("RGB", "L"):
        # Screenshots/webinar grabs often come as RGBA or P.
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        else:
            img = img.convert("RGB")

    meta: dict[str, Any] = {
        "width": img.width,
        "height": img.height,
        "format": (img.format or path.suffix.lstrip(".")).lower(),
        "tessdata": str(bundled_tessdata_dir() or ""),
    }

    # Upscale small captures (compressed webinar stills, phone screenshots).
    shortest = min(img.size)
    if min_side and shortest > 0 and shortest < min_side:
        scale = min_side / float(shortest)
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        meta["original_width"] = orig_w
        meta["original_height"] = orig_h
        meta["upscaled"] = True

    if max_side and max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        meta.setdefault("original_width", orig_w)
        meta.setdefault("original_height", orig_h)

    meta["width"] = img.width
    meta["height"] = img.height

    return img, meta


def prepare_image_for_ocr(image: Any) -> Any:
    """
    Preprocess screenshots/slides for Cyrillic OCR.

    Grayscale, invert dark slides (light text on dark UI), autocontrast,
    light sharpen — typical webinar / landing-page capture profile.
    """
    from PIL import Image, ImageFilter, ImageOps, ImageStat

    if image.mode != "L":
        image = ImageOps.grayscale(image)

    # Dark UI (ChatGPT, Claude, code themes): invert so text is dark-on-light.
    mean = float(ImageStat.Stat(image).mean[0])
    if mean < 110:
        image = ImageOps.invert(image)

    image = ImageOps.autocontrast(image, cutoff=0.5)
    # Mild sharpen helps bold headline fonts without amplifying noise too much.
    image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))
    return image


def ocr_image_to_text(
    image,
    *,
    lang: str = DEFAULT_OCR_LANG,
    psm: int = 3,
    preprocess: bool = True,
    fix_homoglyphs: bool = True,
) -> str:
    """
    Run Tesseract on a PIL Image (or compatible object).

    Uses **bundled** ``tessdata/`` (rus+eng). Applies homoglyph repair so
    ``UEPES`` → ``ЧЕРЕЗ`` while keeping real English (``CLAUDE``).
    """
    configure_pytesseract()
    import pytesseract

    from app.utils.ocr_postprocess import fix_cyrillic_latin_mixups

    tessdata_dir = resolve_tessdata_dir()
    ensure_langs_available(lang, tessdata_dir)

    work = prepare_image_for_ocr(image) if preprocess else image
    # TESSDATA_PREFIX already set in configure_pytesseract() to tessdata_dir.
    # preserve_interword_spaces helps multi-word Russian headlines.
    config = f"--psm {psm} -c preserve_interword_spaces=1"

    try:
        text = pytesseract.image_to_string(work, lang=lang, config=config)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(str(exc)) from exc
    except pytesseract.TesseractError as exc:
        msg = str(exc)
        if "Failed loading language" in msg or "Error opening data file" in msg:
            raise OcrError(
                f"Не удалось загрузить языки OCR «{lang}» из {tessdata_dir}.\n"
                "Запустите .\\scripts\\download_tessdata.ps1"
            ) from exc
        raise OcrError(f"Tesseract error: {msg}") from exc

    text = _normalize_ocr_text(text)
    if fix_homoglyphs:
        text = fix_cyrillic_latin_mixups(text)
    return text


def ocr_image_file(
    path: Path | str,
    *,
    lang: str = DEFAULT_OCR_LANG,
    max_side: int | None = None,
    psm: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """OCR a file on disk. Returns ``(plain_text, image_meta)``."""
    from app.config import OCR_IMAGE_PSM

    if not is_ocr_available():
        raise OcrError(
            "Tesseract OCR не найден. Установите движок:\n"
            "  winget install --id UB-Mannheim.TesseractOCR -e\n"
            "Языковые модели rus+eng поставляются с MD-Converter (папка tessdata/)."
        )
    if psm is None:
        psm = OCR_IMAGE_PSM
    img, meta = load_image_for_ocr(path, max_side=max_side)
    text = ocr_image_to_text(img, lang=lang, psm=psm)
    meta["ocr_lang"] = lang
    meta["ocr_psm"] = psm
    meta["tessdata_dir"] = str(resolve_tessdata_dir())
    return text, meta


def ocr_pixmap_to_text(pix, *, lang: str = DEFAULT_OCR_LANG) -> str:
    """OCR a PyMuPDF Pixmap without writing temp files."""
    from io import BytesIO

    from PIL import Image

    from app.config import OCR_PDF_PSM

    # PNG round-trip is reliable across colorspaces (RGB/Gray/CMYK/alpha).
    img = Image.open(BytesIO(pix.tobytes("png")))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return ocr_image_to_text(img, lang=lang, psm=OCR_PDF_PSM)


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
