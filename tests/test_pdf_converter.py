from pathlib import Path

import fitz

from app.converters.pdf_converter import PdfConverter
from app.models import ConvertOptions, FileJob


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    # Larger title
    page.insert_text((72, 72), "Knowledge Base Manual", fontsize=20)
    page.insert_text((72, 110), "Intro paragraph for the agent.", fontsize=11)
    page.insert_text((72, 140), "• First bullet item", fontsize=11)
    page.insert_text((72, 160), "• Second bullet item", fontsize=11)
    page.insert_text((72, 190), "1. Numbered step", fontsize=11)
    # Simple two-page doc
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Appendix", fontsize=16)
    page2.insert_text((72, 110), "Extra notes on page two.", fontsize=11)
    doc.save(path)
    doc.close()


def test_pdf_conversion(tmp_path: Path):
    src = tmp_path / "manual.pdf"
    _make_pdf(src)
    out_dir = tmp_path / "out"

    job = FileJob(source=src, relative=Path("manual.pdf"))
    options = ConvertOptions(yaml_frontmatter=True)
    result = PdfConverter().convert(job, out_dir, options)

    assert result.ok, result.error
    assert result.outputs
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "---" in md
    assert "type: pdf" in md
    assert "pages: 2" in md
    assert "Intro paragraph" in md
    assert "First bullet" in md or "bullet" in md.lower()
    assert "## Page 1" in md
    assert "## Page 2" in md
    assert "Appendix" in md
    assert result.bytes_out > 0
    assert result.bytes_out < result.bytes_in


def test_pdf_bad_file(tmp_path: Path):
    src = tmp_path / "broken.pdf"
    src.write_bytes(b"%PDF-1.4 not really a pdf")
    job = FileJob(source=src, relative=Path("broken.pdf"))
    result = PdfConverter().convert(job, tmp_path / "out", ConvertOptions())
    assert not result.ok
    assert result.error
