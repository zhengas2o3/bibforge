"""bibforge: a small, dependency-free BibTeX toolkit.

Parse, check, deduplicate, format, search and summarise .bib files
using only the Python standard library.
"""

from .parser import Entry, BibtexSyntaxError, parse, parse_file, split_authors

__version__ = "0.1.0"

__all__ = [
    "Entry",
    "BibtexSyntaxError",
    "parse",
    "parse_file",
    "split_authors",
    "__version__",
]
