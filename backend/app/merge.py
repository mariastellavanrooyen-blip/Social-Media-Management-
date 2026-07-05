import re

CURLY_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
BRACKET_RE = re.compile(r"\[\s*([^\[\]]+?)\s*\]")

# Common natural-language variants people type in [bracket] placeholders, normalized to
# the canonical field names used elsewhere ({{name}}, {{company}}, ...).
ALIASES = {
    "name": "name",
    "first name": "name",
    "full name": "name",
    "client name": "name",
    "contact name": "name",
    "company": "company",
    "company name": "company",
    "business name": "company",
    "business": "company",
    "organization": "company",
    "organisation": "company",
    "email": "email",
    "email address": "email",
    "phone": "phone",
    "phone number": "phone",
    "telephone": "phone",
}


def build_context(row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
    """Merge context = raw uploaded columns, overlaid with canonical field names from the mapping."""
    context = dict(row)
    for target_field, source_column in mapping.items():
        context[target_field] = row.get(source_column, "")
    return context


def _resolve(key: str, context: dict[str, str]) -> str | None:
    """Look up a placeholder name in context: exact match, then case-insensitive, then alias."""
    if key in context:
        return context[key]
    lower = key.strip().lower()
    for context_key, value in context.items():
        if context_key.lower() == lower:
            return value
    canonical = ALIASES.get(lower)
    if canonical and canonical in context:
        return context[canonical]
    return None


def render_template(text: str, context: dict[str, str]) -> str:
    # {{curly}} fields are explicit merge syntax: always resolve, blank if unknown.
    text = CURLY_RE.sub(lambda m: _resolve(m.group(1), context) or "", text)
    # [bracket] fields are a forgiving alias for people used to that convention — only
    # replaced when confidently resolved, otherwise left untouched (never blank real prose
    # that happens to be in square brackets, e.g. "[confidential]").
    text = BRACKET_RE.sub(lambda m: _resolve(m.group(1), context) or m.group(0), text)
    return text


def unknown_fields(text: str, context: dict[str, str]) -> list[str]:
    used = {m.group(1) for m in CURLY_RE.finditer(text)}
    return sorted(k for k in used if _resolve(k, context) is None)
