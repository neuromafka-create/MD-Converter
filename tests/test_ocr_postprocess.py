"""Cyrillic/Latin homoglyph repair after Tesseract."""

from app.utils.ocr_postprocess import fix_cyrillic_latin_mixups


def test_uepes_becomes_cherez():
    raw = "ЛЕНДИНГИ ЗА НЕСКОЛЬКО КЛИКОВ UEPES CLAUDE"
    fixed = fix_cyrillic_latin_mixups(raw)
    assert "ЧЕРЕЗ" in fixed
    assert "UEPES" not in fixed
    assert "CLAUDE" in fixed
    assert "ЛЕНДИНГИ ЗА НЕСКОЛЬКО КЛИКОВ" in fixed


def test_keeps_english_brand_names():
    raw = "Создай промпт для Midjourney и Claude"
    fixed = fix_cyrillic_latin_mixups(raw)
    assert "Midjourney" in fixed
    assert "Claude" in fixed or "Сlaude" not in fixed  # Claude stays Latin
    assert "Создай" in fixed


def test_mixed_script_word():
    # Latin look-alikes inside an otherwise Russian token
    raw = "Пpoмпт для AI"  # р was Latin p/o
    fixed = fix_cyrillic_latin_mixups(raw)
    assert "Промпт" in fixed or "промпт" in fixed.lower()


def test_pure_english_line_untouched():
    raw = "Open PDF file with Claude Desktop"
    assert fix_cyrillic_latin_mixups(raw) == raw
