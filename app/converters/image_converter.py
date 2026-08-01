"""PNG/JPG (and other rasters) → Markdown via Tesseract OCR."""

from __future__ import annotations

from pathlib import Path

from app.config import OCR_IMAGE_MAX_SIDE
from app.converters.base import BaseConverter
from app.core.optimize import optimize_markdown
from app.models import ConvertOptions, ConvertResult, FileJob
from app.utils.markdown import make_frontmatter
from app.utils.ocr import OcrError, ocr_image_file, ocr_text_to_markdown
from app.utils.paths import output_path_for


class ImageConverter(BaseConverter):
    """
    Convert screenshots and photos (webinar slides, etc.) to Markdown.

    Always runs OCR — images have no extractable text layer.
    """

    def convert(
        self,
        job: FileJob,
        output_dir: Path,
        options: ConvertOptions,
    ) -> ConvertResult:
        source = job.source
        try:
            bytes_in = source.stat().st_size
        except OSError as exc:
            return ConvertResult(
                source=source,
                ok=False,
                error=f"Cannot read file: {exc}",
                bytes_in=0,
            )

        # Images always need OCR; honour ocr_mode=off as an explicit refuse.
        if options.ocr_mode == "off":
            return ConvertResult(
                source=source,
                ok=False,
                error=(
                    "Изображения требуют OCR. Включите «OCR для PDF-сканов / изображений» "
                    "в опциях (или ocr_mode=auto)."
                ),
                bytes_in=bytes_in,
            )

        try:
            text, meta = ocr_image_file(
                source,
                lang=options.ocr_lang,
                max_side=OCR_IMAGE_MAX_SIDE,
            )
        except OcrError as exc:
            return ConvertResult(
                source=source,
                ok=False,
                error=str(exc),
                bytes_in=bytes_in,
            )
        except Exception as exc:  # noqa: BLE001
            return ConvertResult(
                source=source,
                ok=False,
                error=f"Image OCR error: {exc}",
                bytes_in=bytes_in,
            )

        body = ocr_text_to_markdown(text)
        title = source.stem
        ext = source.suffix.lower().lstrip(".") or "image"
        # Normalize jpeg → jpg for frontmatter type.
        if ext == "jpeg":
            ext = "jpg"

        parts: list[str] = []
        if options.yaml_frontmatter:
            extra = {
                "ocr": True,
                "ocr_lang": options.ocr_lang,
                "width": meta.get("width"),
                "height": meta.get("height"),
            }
            if meta.get("original_width"):
                extra["original_width"] = meta["original_width"]
                extra["original_height"] = meta["original_height"]
            parts.append(
                make_frontmatter(
                    title=title,
                    source=source,
                    doc_type=ext,
                    extra=extra,
                )
            )
        parts.append(f"# {title}\n")
        parts.append(body or "_No text recognized_\n")

        md = optimize_markdown(
            "\n".join(parts),
            collapse_blank_lines=options.collapse_blank_lines,
        )

        dest = output_path_for(job.source, job.relative, output_dir, options)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(md, encoding="utf-8")
        bytes_out = dest.stat().st_size

        return ConvertResult(
            source=source,
            outputs=[dest],
            ok=True,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
        )
