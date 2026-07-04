from app.merge import build_context, render_template, unknown_fields


def test_build_context_overlays_canonical_fields():
    row = {"Full Name": "Ada Lovelace", "Email Address": "ada@example.com", "Org": "Acme"}
    mapping = {"name": "Full Name", "email": "Email Address", "company": "Org"}
    context = build_context(row, mapping)
    assert context["name"] == "Ada Lovelace"
    assert context["email"] == "ada@example.com"
    assert context["company"] == "Acme"
    # raw uploaded columns remain accessible too
    assert context["Org"] == "Acme"


def test_render_template_substitutes_fields():
    context = {"name": "Ada", "company": "Acme"}
    text = "Hi {{name}}, loved what {{company}} is building."
    assert render_template(text, context) == "Hi Ada, loved what Acme is building."


def test_render_template_missing_field_renders_blank():
    assert render_template("Hi {{name}}, {{missing}}!", {"name": "Ada"}) == "Hi Ada, !"


def test_unknown_fields_detects_unmapped_placeholders():
    context = {"name": "Ada"}
    assert unknown_fields("Hi {{name}}, {{typo}} and {{another}}", context) == ["another", "typo"]


def test_unknown_fields_empty_when_all_known():
    context = {"name": "Ada", "company": "Acme"}
    assert unknown_fields("Hi {{name}} from {{company}}", context) == []
