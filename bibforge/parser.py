"""A small BibTeX parser using only the Python standard library.

Supports:
  * entries delimited by braces ``@article{...}`` or parentheses
    ``@article(...)``
  * braced values with nested braces, quoted values, bare numbers and
    bare identifiers
  * ``@string`` definitions, expanded where they are referenced
  * value concatenation with ``#``
  * ``@comment`` and ``@preamble`` blocks (skipped)
"""

from __future__ import annotations

import re

__all__ = ["Entry", "BibtexSyntaxError", "parse", "parse_file", "split_authors"]


class BibtexSyntaxError(ValueError):
    """Raised when a .bib text cannot be parsed."""


class Entry:
    """One BibTeX entry: a type, a citation key and a field dictionary.

    Field names are stored lower-cased; values are stored as plain
    strings with the outermost braces/quotes removed and whitespace
    collapsed.
    """

    def __init__(self, entry_type: str, key: str, fields: dict):
        self.entry_type = entry_type.lower()
        self.key = key
        self.fields = {name.lower(): value for name, value in fields.items()}

    @property
    def authors(self) -> list:
        """The entry's authors as a list of names."""
        return split_authors(self.fields.get("author", ""))

    def get(self, name: str, default: str = "") -> str:
        return self.fields.get(name.lower(), default)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Entry(@%s{%s, %d fields})" % (
            self.entry_type,
            self.key,
            len(self.fields),
        )

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Entry)
            and self.entry_type == other.entry_type
            and self.key == other.key
            and self.fields == other.fields
        )


def split_authors(author_field: str) -> list:
    """Split a BibTeX ``author`` field on the ``and`` separator."""
    if not author_field:
        return []
    parts = re.split(r"\s+and\s+", author_field.strip())
    return [part.strip() for part in parts if part.strip()]


_ENTRY_START = re.compile(r"@\s*([A-Za-z]+)\s*([{(])")


def parse(text: str) -> list:
    """Parse BibTeX *text* and return a list of :class:`Entry`."""
    strings: dict = {}
    entries: list = []
    pos = 0
    while True:
        match = _ENTRY_START.search(text, pos)
        if match is None:
            break
        entry_type = match.group(1).lower()
        open_ch = match.group(2)
        body_start = match.end()
        body_end = _find_entry_end(text, body_start, open_ch)
        body = text[body_start:body_end]
        pos = body_end + 1

        if entry_type in ("comment", "preamble"):
            continue
        if entry_type == "string":
            name, sep, value = body.partition("=")
            if not sep:
                raise BibtexSyntaxError("malformed @string: %r" % body[:40])
            strings[name.strip().lower()] = _parse_value(value.strip(), strings)
            continue

        key, rest = _split_key(body)
        fields = _parse_fields(rest, strings)
        entries.append(Entry(entry_type, key, fields))
    return entries


def parse_file(path: str) -> list:
    """Read *path* (UTF-8, BOM tolerated) and parse it as BibTeX."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        return parse(handle.read())


def _find_entry_end(text: str, start: int, open_ch: str) -> int:
    """Return the index of the character that closes the entry body."""
    if open_ch == "{":
        depth = 1
        j = start
        while j < len(text):
            char = text[j]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return j
            j += 1
    else:  # '(' — braces inside protect parentheses
        depth = 1
        brace_depth = 0
        j = start
        while j < len(text):
            char = text[j]
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth = max(0, brace_depth - 1)
            elif brace_depth == 0:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        return j
            j += 1
    raise BibtexSyntaxError("unterminated entry starting at offset %d" % start)


def _split_key(body: str) -> tuple:
    """Split an entry body into (citation key, remaining field text)."""
    parts = _split_top_level(body, ",")
    key = parts[0].strip()
    rest = ",".join(parts[1:])
    return key, rest


def _parse_fields(text: str, strings: dict) -> dict:
    fields: dict = {}
    for chunk in _split_top_level(text, ","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, sep, value = chunk.partition("=")
        if not sep:
            raise BibtexSyntaxError("malformed field: %r" % chunk[:40])
        fields[name.strip().lower()] = _parse_value(value.strip(), strings)
    return fields


def _split_top_level(text: str, sep: str) -> list:
    """Split *text* on *sep* occurrences that sit at brace depth 0."""
    parts = []
    current: list = []
    depth = 0
    in_quote = False
    for idx, char in enumerate(text):
        if char == '"' and depth == 0 and (idx == 0 or text[idx - 1] != "\\"):
            in_quote = not in_quote
        if not in_quote:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == sep and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _parse_value(raw: str, strings: dict) -> str:
    """Evaluate a BibTeX value: braces, quotes, numbers, @string refs, ``#``."""
    pieces = []
    for piece in _split_top_level(raw, "#"):
        piece = piece.strip()
        if not piece:
            continue
        if piece.startswith("{"):
            end = _matching_brace(piece)
            inner = piece[1:end]
            pieces.append(re.sub(r"\s+", " ", inner))
        elif piece.startswith('"'):
            end = piece.find('"', 1)
            inner = piece[1:end] if end != -1 else piece[1:]
            pieces.append(re.sub(r"\s+", " ", inner))
        else:
            pieces.append(strings.get(piece.lower(), piece))
    # Whitespace at piece boundaries matters for ``#`` concatenation
    # ("Part " # "One"), so only the joined result is stripped.
    return "".join(pieces).strip()


def _matching_brace(text: str) -> int:
    """Return the index of the brace matching the ``{`` at position 0."""
    depth = 0
    for idx, char in enumerate(text):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return idx
    raise BibtexSyntaxError("unbalanced braces in value: %r" % text[:40])
