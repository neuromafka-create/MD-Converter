from app.core.optimize import optimize_markdown


def test_collapse_blank_lines():
    text = "a\n\n\n\nb\n"
    out = optimize_markdown(text, collapse_blank_lines=True)
    assert out == "a\n\nb\n"


def test_strip_bom_and_trailing_ws():
    text = "\ufeffhello  \nworld\t\n"
    out = optimize_markdown(text)
    assert not out.startswith("\ufeff")
    assert "hello  \n" not in out
    assert out.endswith("\n")


def test_empty():
    assert optimize_markdown("") == ""
