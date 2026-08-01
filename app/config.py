"""Default application settings."""

from __future__ import annotations

APP_NAME = "MD-Converter"
APP_VERSION = "1.1.1"
WINDOW_TITLE = f"{APP_NAME} — DOCX/XLSX/PDF/PNG/JPG → Markdown"
WINDOW_MIN_WIDTH = 920
WINDOW_MIN_HEIGHT = 680

DOCUMENT_EXTENSIONS = {".docx", ".xlsx", ".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# Excel tables wider than this use row-block format instead of GFM pipes.
MAX_GFM_COLUMNS = 12

# Default output subfolder name when user has not chosen a destination.
DEFAULT_OUTPUT_DIRNAME = "md_output"

# PDF OCR (Tesseract): pages with fewer extractable chars trigger OCR in auto mode.
OCR_MIN_CHARS_PER_PAGE = 40
OCR_DPI = 200
OCR_DEFAULT_LANG = "rus+eng"  # models live in project tessdata/ (not system-only eng)
# Longest side of screenshots/scans before OCR (speed vs quality for 4K captures).
OCR_IMAGE_MAX_SIDE = 3000
