"""Command-line interface for bibforge.

Subcommands:
  check   validate a .bib file (duplicate keys, missing fields, years)
  dedup   drop duplicate entries (same DOI or same title)
  format  print the file in canonical format
  search  find entries by author / title / year keyword
  stats   count entries by year and by type
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from .format import format_entries
from .parser import parse_file
from .validate import check as validate_entries
from .validate import dedup_entries

__all__ = ["main", "search_entries"]


def search_entries(entries, query="", author="", title="", year=""):
    """Filter *entries* by keyword criteria (all criteria must match).

    *query* matches against key, author and title; *author*, *title*
    and *year* match against the respective field.  All matching is
    case-insensitive substring matching.
    """
    query = query.lower()
    author = author.lower()
    title = title.lower()
    year = year.strip()
    results = []
    for entry in entries:
        if query:
            haystack = " ".join(
                [entry.key, entry.fields.get("author", ""), entry.fields.get("title", "")]
            ).lower()
            if query not in haystack:
                continue
        if author and author not in entry.fields.get("author", "").lower():
            continue
        if title and title not in entry.fields.get("title", "").lower():
            continue
        if year and entry.fields.get("year", "") != year:
            continue
        results.append(entry)
    return results


def _load(path):
    try:
        return parse_file(path)
    except (OSError, ValueError) as exc:
        print("bibforge: cannot read %s: %s" % (path, exc), file=sys.stderr)
        raise SystemExit(2)


def _emit(text, output):
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)


def cmd_check(args) -> int:
    entries = _load(args.file)
    issues = validate_entries(entries)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    for issue in issues:
        print(str(issue))
    print(
        "%s: %d entries, %d error(s), %d warning(s)"
        % (args.file, len(entries), len(errors), len(warnings))
    )
    return 1 if errors else 0


def cmd_dedup(args) -> int:
    entries = _load(args.file)
    unique, removed = dedup_entries(entries)
    for entry, reason in removed:
        print("removed %s (%s)" % (entry.key, reason), file=sys.stderr)
    print(
        "%s: %d entries -> %d unique, %d duplicate(s) removed"
        % (args.file, len(entries), len(unique), len(removed)),
        file=sys.stderr,
    )
    _emit(format_entries(unique), args.output)
    return 0


def cmd_format(args) -> int:
    entries = _load(args.file)
    _emit(format_entries(entries), args.output)
    return 0


def cmd_search(args) -> int:
    entries = _load(args.file)
    results = search_entries(
        entries,
        query=args.query or "",
        author=args.author or "",
        title=args.title or "",
        year=args.year or "",
    )
    sys.stdout.write(format_entries(results))
    print("%d match(es)" % len(results), file=sys.stderr)
    return 0


def cmd_stats(args) -> int:
    entries = _load(args.file)
    by_type = Counter(entry.entry_type for entry in entries)
    by_year = Counter(entry.fields.get("year", "unknown") or "unknown" for entry in entries)
    print("Total entries: %d" % len(entries))
    print("\nBy type:")
    for name, count in sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-16s %d" % (name, count))
    print("\nBy year:")
    for name, count in sorted(by_year.items()):
        print("  %-16s %d" % (name, count))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bibforge",
        description="A small, dependency-free BibTeX toolkit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="validate a .bib file")
    p_check.add_argument("file", help="path to the .bib file")
    p_check.set_defaults(func=cmd_check)

    p_dedup = sub.add_parser("dedup", help="remove duplicate entries (DOI/title)")
    p_dedup.add_argument("file", help="path to the .bib file")
    p_dedup.add_argument("-o", "--output", help="write here instead of stdout")
    p_dedup.set_defaults(func=cmd_dedup)

    p_format = sub.add_parser("format", help="print the file in canonical format")
    p_format.add_argument("file", help="path to the .bib file")
    p_format.add_argument("-o", "--output", help="write here instead of stdout")
    p_format.set_defaults(func=cmd_format)

    p_search = sub.add_parser("search", help="search entries by keyword")
    p_search.add_argument("file", help="path to the .bib file")
    p_search.add_argument("query", nargs="?", help="keyword matched against key/author/title")
    p_search.add_argument("--author", help="author name substring")
    p_search.add_argument("--title", help="title substring")
    p_search.add_argument("--year", help="exact year, e.g. 2023")
    p_search.set_defaults(func=cmd_search)

    p_stats = sub.add_parser("stats", help="count entries by year and type")
    p_stats.add_argument("file", help="path to the .bib file")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
