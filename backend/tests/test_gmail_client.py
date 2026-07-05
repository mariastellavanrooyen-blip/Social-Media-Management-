from app.gmail_client import plain_text_to_html


def test_plain_text_to_html_preserves_paragraph_breaks():
    text = "Hi Ada,\n\nFirst paragraph.\n\nSecond paragraph."
    result = plain_text_to_html(text)
    assert result == (
        '<p style="margin:0 0 1em;">Hi Ada,</p>'
        '<p style="margin:0 0 1em;">First paragraph.</p>'
        '<p style="margin:0 0 1em;">Second paragraph.</p>'
    )


def test_plain_text_to_html_preserves_single_line_breaks_within_a_paragraph():
    text = "Line one\nLine two"
    assert plain_text_to_html(text) == '<p style="margin:0 0 1em;">Line one<br>Line two</p>'


def test_plain_text_to_html_escapes_special_characters():
    text = "Terms: A & B <script>alert(1)</script>"
    result = plain_text_to_html(text)
    assert "<script>" not in result
    assert "A &amp; B" in result
    assert "&lt;script&gt;" in result


def test_plain_text_to_html_collapses_extra_blank_lines():
    text = "Para one.\n\n\n\nPara two."
    result = plain_text_to_html(text)
    assert result == '<p style="margin:0 0 1em;">Para one.</p><p style="margin:0 0 1em;">Para two.</p>'
