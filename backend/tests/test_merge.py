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


def test_render_template_resolves_bracket_aliases():
    context = {"name": "Ada", "company": "Acme"}
    text = "Hi [First Name], I hear [Business Name] is doing great work."
    assert render_template(text, context) == "Hi Ada, I hear Acme is doing great work."


def test_render_template_bracket_alias_is_case_insensitive():
    context = {"name": "Ada"}
    assert render_template("Hi [first name]!", context) == "Hi Ada!"


def test_render_template_leaves_unresolved_brackets_untouched():
    context = {"name": "Ada"}
    text = "Hi {{name}}, see the [confidential] note below."
    assert render_template(text, context) == "Hi Ada, see the [confidential] note below."


def test_render_template_curly_still_takes_priority_for_raw_columns():
    # Raw uploaded column names must still work via {{Exact Column Name}} — unaffected
    # by the new alias resolution, which only kicks in when there's no exact match.
    context = {"name": "Ada", "First Name": "RawColumnValue"}
    assert render_template("Hi {{First Name}}", context) == "Hi RawColumnValue"


def test_unknown_fields_accounts_for_aliases():
    # "First Name" resolves via alias to "name", so it should not be reported as unknown.
    context = {"name": "Ada"}
    assert unknown_fields("Hi {{First Name}}, {{typo}}", context) == ["typo"]
