import re

MERGE_FIELD_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def build_context(row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
    """Merge context = raw uploaded columns, overlaid with canonical field names from the mapping."""
    context = dict(row)
    for target_field, source_column in mapping.items():
        context[target_field] = row.get(source_column, "")
    return context


def render_template(text: str, context: dict[str, str]) -> str:
    return MERGE_FIELD_RE.sub(lambda m: str(context.get(m.group(1), "")), text)


def unknown_fields(text: str, context: dict[str, str]) -> list[str]:
    used = {m.group(1) for m in MERGE_FIELD_RE.finditer(text)}
    return sorted(used - context.keys())
