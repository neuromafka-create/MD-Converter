"""PDF → Markdown structural converter (PyMuPDF)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from app.converters.base import BaseConverter
from app.core.optimize import optimize_markdown
from app.models import ConvertOptions, ConvertResult, FileJob
from app.utils.markdown import gfm_table, make_frontmatter, normalize_cell_text
from app.utils.paths import output_path_for

_BULLET_RE = re.compile(r"^[\u2022\u2023\u25E6\u2043\u2219•●○▪▫►◆■□\-–—]\s+")
_NUMBERED_RE = re.compile(r"^(\d{1,3})[.)]\s+")
_WS_RE = re.compile(r"[ \t]+")


class PdfConverter(BaseConverter):
    def convert(
        self,
        job: FileJob,
        output_dir: Path,
        options: ConvertOptions,
    ) -> ConvertResult:
        source = job.source
        bytes_in = source.stat().st_size

        try:
            doc = fitz.open(str(source))
        except Exception as exc:  # noqa: BLE001
            return ConvertResult(
                source=source,
                ok=False,
                error=f"PDF open error: {exc}",
                bytes_in=bytes_in,
            )

        try:
            if doc.is_encrypted and not doc.authenticate(""):
                return ConvertResult(
                    source=source,
                    ok=False,
                    error="PDF is password-protected",
                    bytes_in=bytes_in,
                )
            body = self._document_to_markdown(doc, options)
            page_count = doc.page_count
        finally:
            doc.close()

        title = source.stem
        parts: list[str] = []
        if options.yaml_frontmatter:
            parts.append(
                make_frontmatter(
                    title=title,
                    source=source,
                    doc_type="pdf",
                    extra={"pages": page_count},
                )
            )
        parts.append(f"# {title}\n")
        parts.append(body or "_No extractable text_\n")

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

    def _document_to_markdown(self, doc: fitz.Document, options: ConvertOptions) -> str:
        page_blocks: list[str] = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            page_md = self._page_to_markdown(page, options)
            if not page_md.strip():
                continue
            if doc.page_count > 1:
                page_blocks.append(f"## Page {page_index + 1}\n\n{page_md.strip()}")
            else:
                page_blocks.append(page_md.strip())
        return "\n\n".join(page_blocks).strip() + ("\n" if page_blocks else "")

    def _page_to_markdown(self, page: fitz.Page, options: ConvertOptions) -> str:
        table_rects: list[fitz.Rect] = []
        table_md_by_y: list[tuple[float, str]] = []

        # Extract tables first (PyMuPDF table finder); fall back silently if unavailable.
        try:
            finder = page.find_tables()
            tables = list(finder.tables) if finder is not None else []
        except Exception:  # noqa: BLE001
            tables = []

        for table in tables:
            try:
                rect = fitz.Rect(table.bbox)
                raw = table.extract()
            except Exception:  # noqa: BLE001
                continue
            if not raw:
                continue
            rows = [
                [normalize_cell_text(c) for c in row]
                for row in raw
                if row and any(normalize_cell_text(c).strip() for c in row)
            ]
            if not rows:
                continue
            md = gfm_table(rows, header=True)
            if md:
                table_rects.append(rect)
                table_md_by_y.append((rect.y0, md))

        # Text via dict for font-size based heading heuristics.
        data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        body_size = self._estimate_body_size(data)

        text_items: list[tuple[float, str]] = []
        for block in data.get("blocks", []):
            if block.get("type") == 1:
                # Image block
                if options.image_mode == "placeholder":
                    bbox = block.get("bbox") or (0, 0, 0, 0)
                    text_items.append((float(bbox[1]), "![image]()"))
                continue
            if block.get("type") != 0:
                continue

            bbox = block.get("bbox") or (0, 0, 0, 0)
            block_rect = fitz.Rect(bbox)
            # Skip text that sits inside a detected table.
            if any(self._overlap_ratio(block_rect, tr) > 0.5 for tr in table_rects):
                continue

            lines_md = self._block_to_lines(block, body_size)
            if not lines_md:
                continue
            text_items.append((float(bbox[1]), "\n".join(lines_md)))

        # Merge text + tables in reading order (top → bottom).
        merged: list[tuple[float, str]] = text_items + table_md_by_y
        merged.sort(key=lambda item: item[0])

        out_parts: list[str] = []
        prev_list = False
        for _, chunk in merged:
            is_list = self._is_list_line(chunk.split("\n", 1)[0])
            if out_parts and not (is_list and prev_list):
                out_parts.append("")
            out_parts.append(chunk)
            prev_list = is_list

        return "\n".join(out_parts)

    def _estimate_body_size(self, data: dict[str, Any]) -> float:
        sizes: list[float] = []
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    size = float(span.get("size") or 0)
                    if text and size > 0:
                        sizes.append(size)
        if not sizes:
            return 11.0
        sizes.sort()
        # Median as body size
        return sizes[len(sizes) // 2]

    def _block_to_lines(self, block: dict[str, Any], body_size: float) -> list[str]:
        lines_out: list[str] = []
        for line in block.get("lines", []):
            spans = line.get("spans") or []
            if not spans:
                continue
            raw_text = "".join(span.get("text") or "" for span in spans)
            raw_text = _WS_RE.sub(" ", raw_text).strip()
            if not raw_text:
                continue

            max_size = max(float(s.get("size") or 0) for s in spans)
            flags = 0
            for s in spans:
                flags |= int(s.get("flags") or 0)
            # bit 0 superscript, 1 italic, 2 serifed, 3 monospaced, 4 bold (PyMuPDF)
            bold = bool(flags & 2**4) or all(
                "bold" in ((s.get("font") or "").lower()) for s in spans if (s.get("text") or "").strip()
            )

            line_md = self._format_line(raw_text, max_size, body_size, bold)
            if line_md:
                lines_out.append(line_md)
        return lines_out

    def _format_line(self, text: str, size: float, body_size: float, bold: bool) -> str:
        # List detection before heading (bullets often bold).
        bullet = _BULLET_RE.match(text)
        if bullet:
            return f"- {text[bullet.end():].strip()}"
        numbered = _NUMBERED_RE.match(text)
        if numbered:
            return f"1. {text[numbered.end():].strip()}"

        # Heading heuristics by font size relative to body.
        if body_size > 0:
            ratio = size / body_size
            if ratio >= 1.55:
                return f"# {text}"
            if ratio >= 1.35:
                return f"## {text}"
            if ratio >= 1.18 and bold:
                return f"### {text}"

        return text

    @staticmethod
    def _is_list_line(line: str) -> bool:
        s = line.lstrip()
        return s.startswith(("- ", "* ", "+ ")) or bool(re.match(r"^\d+\.\s", s))

    @staticmethod
    def _overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
        inter = a & b
        if inter.is_empty or a.get_area() <= 0:
            return 0.0
        return inter.get_area() / a.get_area()
