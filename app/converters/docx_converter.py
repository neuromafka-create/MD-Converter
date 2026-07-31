"""DOCX → Markdown structural converter."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.converters.base import BaseConverter
from app.core.optimize import optimize_markdown
from app.models import ConvertOptions, ConvertResult, FileJob
from app.utils.markdown import gfm_table, make_frontmatter, normalize_cell_text
from app.utils.paths import output_path_for

_HEADING_RE = re.compile(r"heading\s*(\d)", re.IGNORECASE)


class DocxConverter(BaseConverter):
    def convert(
        self,
        job: FileJob,
        output_dir: Path,
        options: ConvertOptions,
    ) -> ConvertResult:
        source = job.source
        bytes_in = source.stat().st_size

        try:
            document = Document(str(source))
            body = self._document_to_markdown(document, options)
        except Exception as exc:  # noqa: BLE001
            return ConvertResult(
                source=source,
                ok=False,
                error=f"DOCX parse error: {exc}",
                bytes_in=bytes_in,
            )

        title = source.stem
        parts: list[str] = []
        if options.yaml_frontmatter:
            parts.append(
                make_frontmatter(title=title, source=source, doc_type="docx")
            )
        parts.append(f"# {title}\n")
        parts.append(body)

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

    def _document_to_markdown(self, document: DocumentType, options: ConvertOptions) -> str:
        blocks: list[str] = []
        # Iterate body elements in document order (paragraphs + tables interleaved).
        for element in document.element.body:
            tag = element.tag
            if tag == qn("w:p"):
                para = Paragraph(element, document)
                line = self._paragraph_to_md(para, document, options)
                if line is not None:
                    blocks.append(line)
            elif tag == qn("w:tbl"):
                table = Table(element, document)
                md_table = self._table_to_md(table)
                if md_table:
                    blocks.append(md_table)
                    blocks.append("")  # spacing after table

        # Join paragraphs carefully: headings/lists already include structure.
        return self._join_blocks(blocks)

    def _join_blocks(self, blocks: list[str]) -> str:
        """Join blocks with blank lines, keeping list items tightly grouped."""
        out: list[str] = []
        prev_list = False
        for block in blocks:
            if block == "":
                if out and out[-1] != "":
                    out.append("")
                prev_list = False
                continue
            is_list = bool(
                block.lstrip().startswith(("- ", "* ", "+ "))
                or (len(block.lstrip()) > 2 and block.lstrip()[0].isdigit() and ". " in block.lstrip()[:4])
            )
            is_heading = block.startswith("#")
            is_table = block.startswith("|")
            if out and out[-1] != "":
                # Tight grouping only for consecutive list items.
                if not (is_list and prev_list):
                    out.append("")
            out.append(block)
            prev_list = is_list and not is_heading and not is_table
        return "\n".join(out).strip() + ("\n" if out else "")

    def _paragraph_to_md(
        self,
        para: Paragraph,
        document: DocumentType,
        options: ConvertOptions,
    ) -> str | None:
        style_name = ""
        try:
            if para.style is not None and para.style.name:
                style_name = para.style.name
        except Exception:  # noqa: BLE001
            style_name = ""

        # Images / drawings without text.
        has_drawing = bool(para._element.xpath(".//*[local-name()='drawing' or local-name()='pict']"))
        text_md = self._runs_to_md(para)

        if not text_md.strip():
            if has_drawing and options.image_mode == "placeholder":
                return "![image]()"
            if has_drawing and options.image_mode == "skip":
                return None
            return None

        heading_level = self._heading_level(style_name)
        if heading_level:
            return f"{'#' * heading_level} {text_md.strip()}"

        list_info = self._list_prefix(para, document, style_name)
        if list_info is not None:
            indent, marker = list_info
            return f"{'  ' * indent}{marker} {text_md.strip()}"

        # Quote-like styles
        lower = style_name.lower()
        if "quote" in lower:
            lines = text_md.strip().split("\n")
            return "\n".join(f"> {ln}" if ln else ">" for ln in lines)

        return text_md.strip()

    def _heading_level(self, style_name: str) -> int | None:
        if not style_name:
            return None
        m = _HEADING_RE.search(style_name)
        if m:
            level = int(m.group(1))
            return max(1, min(level, 6))
        # Title → H1
        if style_name.lower() in {"title", "название"}:
            return 1
        if style_name.lower() in {"subtitle", "подзаголовок"}:
            return 2
        return None

    def _list_prefix(
        self,
        para: Paragraph,
        document: DocumentType,
        style_name: str,
    ) -> tuple[int, str] | None:
        """Return (indent_level, marker) if paragraph is a list item."""
        lower = (style_name or "").lower()

        # Style-name heuristics (python-docx List Bullet / List Number, RU locales, etc.)
        style_bullet = any(
            key in lower
            for key in (
                "list bullet",
                "list paragraph",
                "bullet",
                "маркированн",
                "маркированный",
            )
        )
        style_number = any(
            key in lower
            for key in (
                "list number",
                "list continue",
                "numbered",
                "нумеров",
                "нумерованный",
            )
        )

        pPr = para._element.pPr
        numPr = pPr.numPr if pPr is not None else None

        if numPr is None and not style_bullet and not style_number:
            return None

        ilvl = 0
        if numPr is not None and numPr.ilvl is not None and numPr.ilvl.val is not None:
            ilvl = int(numPr.ilvl.val)

        if style_number:
            is_number = True
        elif style_bullet:
            is_number = False
        else:
            is_number = self._is_numbered(para, document)

        marker = "1." if is_number else "-"
        return ilvl, marker

    def _is_numbered(self, para: Paragraph, document: DocumentType) -> bool:
        try:
            pPr = para._element.pPr
            if pPr is None or pPr.numPr is None or pPr.numPr.numId is None:
                return False
            num_id = pPr.numPr.numId.val
            if num_id is None:
                return False
            numbering = document.part.numbering_part
            if numbering is None:
                return False
            # Heuristic: look for numFmt decimal/etc in abstract numbering.
            root = numbering._element
            for num in root.findall(qn("w:num")):
                if num.get(qn("w:numId")) == str(num_id):
                    abs_id_el = num.find(qn("w:abstractNumId"))
                    if abs_id_el is None:
                        break
                    abs_id = abs_id_el.get(qn("w:val"))
                    for abs_num in root.findall(qn("w:abstractNum")):
                        if abs_num.get(qn("w:abstractNumId")) == abs_id:
                            for lvl in abs_num.findall(qn("w:lvl")):
                                fmt = lvl.find(qn("w:numFmt"))
                                if fmt is not None:
                                    val = fmt.get(qn("w:val")) or ""
                                    if val in {
                                        "decimal",
                                        "lowerLetter",
                                        "upperLetter",
                                        "lowerRoman",
                                        "upperRoman",
                                        "decimalZero",
                                    }:
                                        return True
                                    if val in {"bullet", "none"}:
                                        return False
                    break
        except Exception:  # noqa: BLE001
            return False
        return False

    def _runs_to_md(self, para: Paragraph) -> str:
        """Convert paragraph runs with basic inline formatting."""
        # Handle hyperlinks at paragraph XML level for better fidelity.
        pieces: list[str] = []
        for child in para._element:
            tag = child.tag
            if tag == qn("w:r"):
                pieces.append(self._run_element_to_md(child))
            elif tag == qn("w:hyperlink"):
                pieces.append(self._hyperlink_to_md(child, para))
            # skip bookmarks, proofErr, etc.
        return "".join(pieces)

    def _hyperlink_to_md(self, hyperlink_el, para: Paragraph) -> str:
        text_parts: list[str] = []
        for r in hyperlink_el.findall(qn("w:r")):
            text_parts.append(self._run_element_to_md(r))
        label = "".join(text_parts).strip() or "link"
        r_id = hyperlink_el.get(qn("r:id"))
        url = ""
        if r_id:
            try:
                rel = para.part.rels[r_id]
                url = rel.target_ref
            except Exception:  # noqa: BLE001
                url = ""
        if url:
            return f"[{label}]({url})"
        return label

    def _run_element_to_md(self, run_el) -> str:
        texts = [t.text or "" for t in run_el.findall(qn("w:t"))]
        text = "".join(texts)
        if not text:
            # soft line break
            if run_el.find(qn("w:br")) is not None:
                return "\n"
            if run_el.find(qn("w:tab")) is not None:
                return " "
            return ""

        rPr = run_el.find(qn("w:rPr"))
        bold = italic = strike = code = False
        if rPr is not None:
            bold = rPr.find(qn("w:b")) is not None and not _is_val_false(rPr.find(qn("w:b")))
            italic = rPr.find(qn("w:i")) is not None and not _is_val_false(rPr.find(qn("w:i")))
            strike = rPr.find(qn("w:strike")) is not None and not _is_val_false(
                rPr.find(qn("w:strike"))
            )
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is not None:
                ascii_font = (rFonts.get(qn("w:ascii")) or "").lower()
                if any(x in ascii_font for x in ("consolas", "courier", "mono", "cambria math")):
                    code = True
            # style-based code
            rStyle = rPr.find(qn("w:rStyle"))
            if rStyle is not None:
                style_val = (rStyle.get(qn("w:val")) or "").lower()
                if "code" in style_val or "verbatim" in style_val:
                    code = True

        if code:
            return f"`{text}`"
        if strike:
            text = f"~~{text}~~"
        if bold and italic:
            text = f"***{text}***"
        elif bold:
            text = f"**{text}**"
        elif italic:
            text = f"*{text}*"
        return text

    def _table_to_md(self, table: Table) -> str:
        rows: list[list[str]] = []
        for row in table.rows:
            cells = [normalize_cell_text(cell.text) for cell in row.cells]
            # python-docx repeats merged cell text; de-dupe consecutive identical in row.
            cells = _dedupe_merged_row(cells)
            rows.append(cells)
        # Drop fully empty rows
        rows = [r for r in rows if any(c.strip() for c in r)]
        if not rows:
            return ""
        return gfm_table(rows, header=True)


def _is_val_false(el) -> bool:
    if el is None:
        return True
    val = el.get(qn("w:val"))
    if val is None:
        return False
    return val in {"0", "false", "off"}


def _dedupe_merged_row(cells: list[str]) -> list[str]:
    """Collapse consecutive identical cell values (common with horizontal merges)."""
    if not cells:
        return cells
    out = [cells[0]]
    for c in cells[1:]:
        if c == out[-1] and c != "":
            # keep one empty placeholder for structure? Drop duplicate merge.
            continue
        out.append(c)
    # If we collapsed too aggressively and only one cell left from many merges,
    # still OK for markdown. Re-expand? Prefer cleaner tables for agents.
    return out if out else cells
