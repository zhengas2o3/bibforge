"""Validation and de-duplication for parsed BibTeX entries."""

from __future__ import annotations

import re
from collections import Counter

__all__ = [
    "Issue",
    "REQUIRED_FIELDS",
    "check",
    "find_duplicate_keys",
    "normalize_doi",
    "normalize_title",
    "dedup_entries",
]


# Required fields per entry type (BibTeX standard).  ``book`` and
# ``inbook`` additionally need an author *or* an editor; that is checked
# separately in :func:`check`.
REQUIRED_FIELDS = {
    "article": ["author", "title", "journal", "year"],
    "book": ["title", "publisher", "year"],
    "inbook": ["title", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "conference": ["author", "title", "booktitle", "year"],
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "unpublished": ["author", "title", "note"],
    "misc": ["title"],
}

_YEAR_RE = re.compile(r"^\d{4}$")


class Issue:
    """A single validation finding."""

    def __init__(self, level: str, key: str, message: str):
        self.level = level  # "error" or "warning"
        self.key = key
        self.message = message

    def __str__(self) -> str:
        return "%s [%s] %s" % (self.level.upper(), self.key, self.message)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Issue(%r, %r, %r)" % (self.level, self.key, self.message)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Issue)
            and (self.level, self.key, self.message)
            == (other.level, other.key, other.message)
        )


def find_duplicate_keys(entries: list) -> dict:
    """Return ``{key: count}`` for citation keys occurring more than once."""
    counts = Counter(entry.key.lower() for entry in entries)
    return {key: n for key, n in counts.items() if n > 1}


def check(entries: list) -> list:
    """Validate *entries* and return a list of :class:`Issue`.

    Checks performed:
      * duplicate citation keys (error)
      * missing required fields for the entry type (error)
      * ``book``/``inbook`` entries with neither author nor editor (error)
      * a ``year`` field that is not a four-digit year (warning)
      * empty field values (warning)
    """
    issues: list = []

    for key, count in sorted(find_duplicate_keys(entries).items()):
        issues.append(
            Issue("error", key, "duplicate citation key (%d occurrences)" % count)
        )

    for entry in entries:
        required = REQUIRED_FIELDS.get(entry.entry_type)
        if required is None:
            issues.append(
                Issue(
                    "warning",
                    entry.key,
                    "unknown entry type @%s; required fields not checked"
                    % entry.entry_type,
                )
            )
        else:
            for field in required:
                if not entry.fields.get(field):
                    issues.append(
                        Issue(
                            "error",
                            entry.key,
                            "missing required field '%s' for @%s"
                            % (field, entry.entry_type),
                        )
                    )
            if entry.entry_type in ("book", "inbook"):
                if not entry.fields.get("author") and not entry.fields.get("editor"):
                    issues.append(
                        Issue(
                            "error",
                            entry.key,
                            "missing required field 'author' (or 'editor') for @%s"
                            % entry.entry_type,
                        )
                    )

        year = entry.fields.get("year")
        if year and not _YEAR_RE.match(year.strip()):
            issues.append(
                Issue(
                    "warning",
                    entry.key,
                    "year %r is not a four-digit year" % year,
                )
            )

        for name, value in entry.fields.items():
            if not value.strip():
                issues.append(
                    Issue("warning", entry.key, "field '%s' is empty" % name)
                )

    return issues


def normalize_doi(doi: str) -> str:
    """Normalise a DOI for comparison: lower-case, no URL/scheme prefix."""
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.strip()


def normalize_title(title: str) -> str:
    """Normalise a title for comparison: lower-case, alphanumerics only."""
    return "".join(char for char in title.lower() if char.isalnum())


def dedup_entries(entries: list) -> tuple:
    """Remove duplicate entries, keeping the first occurrence.

    Two entries are duplicates when they share a non-empty normalised
    DOI, or a non-empty normalised title.  Returns ``(unique, removed)``
    where *removed* is a list of ``(entry, reason)`` pairs.
    """
    seen_doi: dict = {}
    seen_title: dict = {}
    unique: list = []
    removed: list = []
    for entry in entries:
        doi = normalize_doi(entry.fields.get("doi", ""))
        title = normalize_title(entry.fields.get("title", ""))
        if doi and doi in seen_doi:
            removed.append((entry, "same DOI as '%s'" % seen_doi[doi]))
            continue
        if title and title in seen_title:
            removed.append((entry, "same title as '%s'" % seen_title[title]))
            continue
        if doi:
            seen_doi[doi] = entry.key
        if title:
            seen_title[title] = entry.key
        unique.append(entry)
    return unique, removed
