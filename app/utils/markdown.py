"""Markdown helpers: GFM tables, frontmatter, cell normalization."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence


def normalize_cell_text(value: Any) -> str:
    """Convert a cell/run value to a compact single-line string."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.hour == 0 and value.minute == 0 and value.second == 0 and value.microsecond == 0:
            return value.date().isoformat()
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        text = f"{value:.10g}"
        return text
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    # Tables: keep cell content on one logical line.
    text = text.replace("\n", " ").strip()
    return text


def escape_table_cell(text: str) -> str:
    """Escape pipe characters so GFM tables stay valid."""
    return text.replace("|", "\\|").replace("\n", " ")


def gfm_table(rows: Sequence[Sequence[str]], *, header: bool = True) -> str:
    """
    Build a GitHub-Flavored Markdown table.

    If header is True, the first row is treated as the header.
    Empty input returns an empty string.
    """
    if not rows:
        return ""

    normalized: list[list[str]] = [
        [escape_table_cell(normalize_cell_text(c)) for c in row] for row in rows
    ]
    width = max(len(r) for r in normalized)
    if width == 0:
        return ""

    for row in normalized:
        if len(row) < width:
            row.extend([""] * (width - len(row)))

    def fmt_row(cells: Sequence[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    lines: list[str] = []
    if header:
        head = normalized[0]
        body = normalized[1:]
        # Avoid empty header cells (GFM still works, but ugly).
        head = [c if c else " " for c in head]
        lines.append(fmt_row(head))
        lines.append("| " + " | ".join(["---"] * width) + " |")
        for row in body:
            lines.append(fmt_row(row))
    else:
        # Synthetic header for pure data grids.
        head = [f"Col{i + 1}" for i in range(width)]
        lines.append(fmt_row(head))
        lines.append("| " + " | ".join(["---"] * width) + " |")
        for row in normalized:
            lines.append(fmt_row(row))

    return "\n".join(lines)


def make_frontmatter(
    *,
    title: str,
    source: Path | str,
    doc_type: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """YAML frontmatter block for agent-friendly metadata."""
    source_str = str(source).replace("\\", "/")
    lines = [
        "---",
        f'title: "{_yaml_escape(title)}"',
        f'source: "{_yaml_escape(source_str)}"',
        f"type: {doc_type}",
        f'converted_at: "{datetime.now().isoformat(timespec="seconds")}"',
    ]
    if extra:
        for key, value in extra.items():
            if isinstance(value, bool):
                lines.append(f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                lines.append(f'{key}: "{_yaml_escape(str(value))}"')
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _yaml_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
