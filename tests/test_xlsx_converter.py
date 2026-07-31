from datetime import date
from pathlib import Path

from openpyxl import Workbook

from app.converters.xlsx_converter import XlsxConverter
from app.models import ConvertOptions, FileJob


def _make_xlsx(path: Path) -> None:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Sales"
    ws1.append(["Product", "Qty", "Date"])
    ws1.append(["Widget", 3, date(2024, 1, 15)])
    ws1.append([None, None, None])  # empty row
    ws1.append(["Gadget", 1, date(2024, 2, 1)])

    ws2 = wb.create_sheet("Notes")
    ws2.append(["Note"])
    ws2.append(["Hello world"])
    wb.save(path)


def test_xlsx_single_file(tmp_path: Path):
    src = tmp_path / "book.xlsx"
    _make_xlsx(src)
    out_dir = tmp_path / "out"

    job = FileJob(source=src, relative=Path("book.xlsx"))
    options = ConvertOptions(skip_empty_excel_rows=True, excel_one_file_per_sheet=False)
    result = XlsxConverter().convert(job, out_dir, options)

    assert result.ok, result.error
    assert len(result.outputs) == 1
    md = result.outputs[0].read_text(encoding="utf-8")
    assert "## Sales" in md
    assert "## Notes" in md
    assert "Widget" in md
    assert "2024-01-15" in md
    # empty row skipped — should not produce sparse junk only
    assert "Hello world" in md
    assert result.bytes_out < result.bytes_in


def test_xlsx_per_sheet(tmp_path: Path):
    src = tmp_path / "book.xlsx"
    _make_xlsx(src)
    out_dir = tmp_path / "out"

    job = FileJob(source=src, relative=Path("book.xlsx"))
    options = ConvertOptions(excel_one_file_per_sheet=True)
    result = XlsxConverter().convert(job, out_dir, options)

    assert result.ok, result.error
    assert len(result.outputs) == 2
