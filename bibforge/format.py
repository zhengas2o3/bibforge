"""Canonical formatting for BibTeX entries.

Entries are printed with a two-space indent, one field per line, fields
in a canonical order (author, title, venue, year, ... then the rest
alphabetically) and every value wrapped in braces.
"""

from __future__ import annotations

__all__ = ["FIELD_ORDER", "format_entry", "format_entries"]

FIELD_ORDER = [
    "author",
    "editor",
    "title",
    "booktitle",
    "journal",
    "year",
    "month",
    "volume",
    "number",
    "pages",
    "publisher",
    "address",
    "edition",
    "series",
    "school",
    "institution",
    "doi",
    "url",
    "isbn",
    "issn",
    "note",
    "abstract",
    "keywords",
]

_ORDER_INDEX = {name: idx for idx, name in enumerate(FIELD_ORDER)}


def _field_sort_key(name: str) -> tuple:
    return (_ORDER_INDEX.get(name, len(FIELD_ORDER)), name)


def format_entry(entry) -> str:
    """Return *entry* as a canonically formatted BibTeX block."""
    lines = ["@%s{%s," % (entry.entry_type, entry.key)]
    names = sorted(entry.fields, key=_field_sort_key)
    for idx, name in enumerate(names):
        comma = "," if idx < len(names) - 1 else ""
        lines.append("  %s = {%s}%s" % (name, entry.fields[name], comma))
    lines.append("}")
    return "\n".join(lines)


def format_entries(entries) -> str:
    """Format a list of entries, separated by blank lines."""
    if not entries:
        return ""
    return "\n\n".join(format_entry(entry) for entry in entries) + "\n"
