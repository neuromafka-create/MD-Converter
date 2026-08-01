"""
Post-process Tesseract output for Russian + English mixes.

With ``rus+eng``, Cyrillic letters that look like Latin (Р/P, С/C, З/S, Ч≈U …)
are often emitted as Latin, producing junk like ``UEPES`` instead of ``ЧЕРЕЗ``.
Real English tokens (``CLAUDE``, ``Midjourney``) must stay Latin.
"""

from __future__ import annotations

import re

# Latin → Cyrillic look-alikes / frequent OCR confusions for Russian slides.
_LATIN_TO_CYR = str.maketrans(
    {
        "A": "А",
        "a": "а",
        "B": "В",
        "C": "С",
        "c": "с",
        "E": "Е",
        "e": "е",
        "H": "Н",
        "K": "К",
        "k": "к",
        "M": "М",
        "m": "м",
        "O": "О",
        "o": "о",
        "P": "Р",
        "p": "р",
        "T": "Т",
        "t": "т",
        "X": "Х",
        "x": "х",
        "Y": "У",
        "y": "у",
        # Common headline misreads (not strict visual twins, but frequent):
        "U": "Ч",
        "u": "ч",
        "S": "З",
        "s": "з",
        "Z": "З",
        "z": "з",
        "N": "И",  # И misread as N in some fonts
        "V": "У",
        "W": "Ш",
        "w": "ш",
    }
)

# Latin letters that almost never appear as Cyrillic look-alikes in mixed OCR.
# Presence ⇒ keep the word as English (e.g. CLAUDE, Midjourney, PDF).
_LATIN_ONLY_MARKERS = frozenset("DdFfGgJjLlQqRrVvWw")

_WORD_RE = re.compile(
    r"[A-Za-zА-Яа-яЁёІіЇїЄєҐґ]+(?:['’-][A-Za-zА-Яа-яЁёІіЇїЄєҐґ]+)*|[0-9]+|[^\w\s]|[\s]+",
    re.UNICODE,
)

_CYR_RE = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]")
_LAT_RE = re.compile(r"[A-Za-z]")


def _is_cyrillic(ch: str) -> bool:
    return bool(_CYR_RE.fullmatch(ch)) if len(ch) == 1 else bool(_CYR_RE.search(ch))


def _is_latin_letter(ch: str) -> bool:
    return ("A" <= ch <= "Z") or ("a" <= ch <= "z")


def _letters(token: str) -> str:
    return "".join(ch for ch in token if ch.isalpha())


def _all_latin_confusable(token: str) -> bool:
    """True if every Latin letter in token has a Cyrillic mapping."""
    letters = _letters(token)
    if not letters:
        return False
    for ch in letters:
        if _is_latin_letter(ch):
            if ch in _LATIN_ONLY_MARKERS:
                return False
            if ch not in _LATIN_TO_CYR:
                # translate table uses ord keys — check via try
                if ch.translate(_LATIN_TO_CYR) == ch:
                    return False
        elif not _is_cyrillic(ch):
            return False
    return True


def _to_cyrillic(token: str) -> str:
    return token.translate(_LATIN_TO_CYR)


def _fix_token(token: str, *, prefer_cyrillic: bool) -> str:
    letters = _letters(token)
    if not letters:
        return token

    has_cyr = bool(_CYR_RE.search(letters))
    has_lat = bool(_LAT_RE.search(letters))

    if has_cyr and has_lat:
        # Mixed script word (e.g. "Пpoмпт") — force confusable Latin → Cyrillic.
        return _to_cyrillic(token)

    if has_lat and not has_cyr:
        # Pure Latin: convert only confusable clusters (UEPES→ЧЕРЕЗ), keep CLAUDE.
        if prefer_cyrillic and _all_latin_confusable(token) and len(letters) >= 2:
            return _to_cyrillic(token)
        return token

    return token


def fix_cyrillic_latin_mixups(text: str) -> str:
    """
    Repair Latin look-alikes inside Russian OCR text.

    Lines that already contain Cyrillic bias conversion of pure-Latin
    confusable tokens (``UEPES`` → ``ЧЕРЕЗ``). English words with
    distinctive Latin letters stay unchanged (``CLAUDE``).
    """
    if not text or not _LAT_RE.search(text):
        return text

    out_lines: list[str] = []
    for line in text.split("\n"):
        if not line.strip() or not _LAT_RE.search(line):
            out_lines.append(line)
            continue

        # Prefer Cyrillic fixups when the line already has Russian, or when
        # every Latin word on the line is confusable (all-caps Russian slide).
        line_has_cyr = bool(_CYR_RE.search(line))
        tokens = _WORD_RE.findall(line)
        latin_words = [
            t
            for t in tokens
            if _LAT_RE.search(t) and not _CYR_RE.search(t) and _letters(t)
        ]
        all_confusable = bool(latin_words) and all(_all_latin_confusable(t) for t in latin_words)
        prefer = line_has_cyr or all_confusable

        fixed: list[str] = []
        for tok in tokens:
            if _LAT_RE.search(tok):
                fixed.append(_fix_token(tok, prefer_cyrillic=prefer))
            else:
                fixed.append(tok)
        out_lines.append("".join(fixed))

    return "\n".join(out_lines)
