# bibforge

A small, dependency-free BibTeX toolkit — parse, check, deduplicate, format, search and summarise `.bib` files using only the Python standard library.

## Features

- **Parser** for `.bib` files: braced values with nested braces, quoted values, bare numbers/identifiers, `@string` definitions with expansion, value concatenation with `#`, and entries delimited by braces or parentheses
- **check** — validate a bibliography: duplicate citation keys, missing required fields per entry type, malformed years, empty fields
- **dedup** — drop duplicate entries that share a DOI (prefixes like `https://doi.org/` are normalised) or the same title
- **format** — canonical output: fields in a fixed order (author, title, venue, year, …), two-space indent, one field per line
- **search** — find entries by keyword, author, title or year
- **stats** — count entries by year and by entry type
- Zero third-party dependencies; runs on Python 3.9+

## Installation

```bash
git clone https://github.com/zhengas2o3/bibforge.git
cd bibforge
pip install .
```

This installs the `bibforge` command. Without installing, run it as a module from the project root: `python -m bibforge.cli <command> ...`.

## Usage

The examples below use `examples/sample.bib`, a small bibliography that deliberately contains a duplicate citation key and an entry with a missing field.

### Check a bibliography

```console
$ bibforge check examples/sample.bib
ERROR [smith2020] duplicate citation key (2 occurrences)
ERROR [lee2019] missing required field 'journal' for @article
WARNING [wang2023] year '202' is not a four-digit year
examples/sample.bib: 8 entries, 2 error(s), 1 warning(s)
```

`check` exits with status 1 when errors are found, so it can gate a build or CI job.

### Statistics

```console
$ bibforge stats examples/sample.bib
Total entries: 8

By type:
  article          5
  book             1
  inproceedings    1
  misc             1

By year:
  1984             1
  2019             1
  202              1
  2020             1
  2021             2
  2022             2
```

### Format

```console
$ bibforge format examples/sample.bib
@article{smith2020,
  author = {Smith, John and Doe, Jane},
  title = {A Study of {BibTeX} Workflows},
  journal = {Journal of Machine Learning Research},
  year = {2020},
  volume = {21},
  pages = {1--15},
  doi = {10.1000/xyz123}
}
...
```

Note how the `@string` reference `journal = ml` in the source file is expanded in the output. Use `-o FILE` to write to a file instead of stdout.

### Remove duplicates

```console
$ bibforge dedup examples/sample.bib -o cleaned.bib
removed chen2022preprint (same DOI as 'chen2022')
examples/sample.bib: 8 entries -> 7 unique, 1 duplicate(s) removed
```

The cleaned, canonically formatted bibliography is written to `cleaned.bib`; the report goes to stderr.

### Search

```console
$ bibforge search examples/sample.bib --author smith
@article{smith2020,
  author = {Smith, John and Doe, Jane},
  ...
}
...
3 match(es)
```

A positional keyword matches against key, author and title; `--author`, `--title` and `--year` narrow the search further (all criteria combine).

## Project structure

```
bibforge/
├── bibforge/
│   ├── __init__.py    # public API (Entry, parse, parse_file)
│   ├── parser.py      # BibTeX parser (@string expansion included)
│   ├── validate.py    # validation checks and de-duplication
│   ├── format.py      # canonical formatting
│   └── cli.py         # argparse CLI: check / dedup / format / search / stats
├── examples/
│   └── sample.bib     # demo bibliography (with deliberate flaws)
├── tests/
│   └── test_bibforge.py
├── pyproject.toml
└── README.md
```

## Development

Run the test suite (standard-library `unittest`, no extra installs needed):

```bash
python -m unittest discover -s tests
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Ruizhao Zheng.
