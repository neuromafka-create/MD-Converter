"""Post-process Markdown to reduce volume without losing structure."""

from __future__ import annotations

import re

_MULTI_BLANK = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_TRAILING_WS_EOF = re.compile(r"[ \t]+$")


def optimize_markdown(text: str, *, collapse_blank_lines: bool = True) -> str:
    """
    Normalize and lightly compress Markdown for agent knowledge bases.

    - Normalize newlines to \\n
    - Strip BOM
    - Trim trailing whitespace on lines
    - Collapse 3+ blank lines to a single blank line (optional)
    - Ensure file ends with a single newline
    """
    if not text:
        return ""

    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRAILING_WS.sub("\n", text)
    text = _TRAILING_WS_EOF.sub("", text)

    if collapse_blank_lines:
        text = _MULTI_BLANK.sub("\n\n", text)

    text = text.strip("\n")
    if text:
        text += "\n"
    return text
