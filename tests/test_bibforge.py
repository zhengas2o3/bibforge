import unittest

from bibforge import parse
from bibforge.cli import search_entries
from bibforge.format import format_entries, format_entry
from bibforge.validate import check, dedup_entries, normalize_doi, normalize_title


SAMPLE = """
@article{smith2020,
  author  = {Smith, John and Doe, Jane},
  title   = {A Study of {BibTeX} Workflows},
  journal = {Journal of Examples},
  year    = {2020},
  doi     = {10.1000/xyz123}
}

@book{knuth1984,
  author    = "Knuth, Donald E.",
  title     = "The TeXbook",
  publisher = {Addison-Wesley},
  year      = 1984
}
"""


class TestParser(unittest.TestCase):
    def test_parse_basic_entry(self):
        entries = parse(SAMPLE)
        self.assertEqual(len(entries), 2)
        first = entries[0]
        self.assertEqual(first.entry_type, "article")
        self.assertEqual(first.key, "smith2020")
        self.assertEqual(first.fields["journal"], "Journal of Examples")
        self.assertEqual(first.fields["year"], "2020")

    def test_parse_quoted_and_bare_values(self):
        entries = parse(SAMPLE)
        book = entries[1]
        self.assertEqual(book.fields["author"], "Knuth, Donald E.")
        self.assertEqual(book.fields["year"], "1984")

    def test_parse_nested_braces_kept(self):
        entries = parse(SAMPLE)
        self.assertEqual(entries[0].fields["title"], "A Study of {BibTeX} Workflows")

    def test_parse_authors_split(self):
        entries = parse(SAMPLE)
        self.assertEqual(entries[0].authors, ["Smith, John", "Doe, Jane"])
        self.assertEqual(entries[1].authors, ["Knuth, Donald E."])

    def test_parse_string_expansion(self):
        text = """
        @string{jmlr = {Journal of Machine Learning Research}}
        @article{a2020, author={A, Ann}, title={T}, journal=jmlr, year={2020}}
        """
        entries = parse(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0].fields["journal"], "Journal of Machine Learning Research"
        )

    def test_parse_value_concatenation(self):
        text = '@article{a, author={A}, title="Part " # "One", journal={J}, year={2001}}'
        entries = parse(text)
        self.assertEqual(entries[0].fields["title"], "Part One")

    def test_parse_parentheses_entry(self):
        text = "@misc(x1, title={Note}, year={1999})"
        entries = parse(text)
        self.assertEqual(entries[0].entry_type, "misc")
        self.assertEqual(entries[0].key, "x1")

    def test_parse_ignores_comments_and_preamble(self):
        text = "% a comment\n@comment{ignore me}\n@preamble{\"x\"}\n" + SAMPLE
        self.assertEqual(len(parse(text)), 2)


class TestValidate(unittest.TestCase):
    def test_check_clean_bib_has_no_errors(self):
        issues = check(parse(SAMPLE))
        self.assertEqual([i for i in issues if i.level == "error"], [])

    def test_check_duplicate_key(self):
        text = SAMPLE + "\n@article{smith2020, author={S}, title={T}, journal={J}, year={2022}}\n"
        issues = check(parse(text))
        errors = [i.message for i in issues if i.level == "error"]
        self.assertTrue(any("duplicate citation key" in m for m in errors))

    def test_check_missing_required_field(self):
        text = "@article{bad, author={A}, title={T}, year={2019}}"
        issues = check(parse(text))
        errors = [i.message for i in issues if i.level == "error"]
        self.assertTrue(any("'journal'" in m for m in errors))

    def test_check_book_needs_author_or_editor(self):
        text = "@book{bad, title={T}, publisher={P}, year={2000}}"
        issues = check(parse(text))
        self.assertTrue(any(i.level == "error" for i in issues))
        ok = "@book{good, editor={E, Ed}, title={T}, publisher={P}, year={2000}}"
        issues = check(parse(ok))
        self.assertEqual([i for i in issues if i.level == "error"], [])

    def test_check_year_format_warning(self):
        text = "@misc{bad, title={T}, year={202}}"
        issues = check(parse(text))
        warnings = [i.message for i in issues if i.level == "warning"]
        self.assertTrue(any("four-digit year" in m for m in warnings))


class TestDedup(unittest.TestCase):
    def test_normalize_helpers(self):
        self.assertEqual(normalize_doi("https://doi.org/10.1000/ABC"), "10.1000/abc")
        self.assertEqual(normalize_title("A Study of BibTeX!"), "astudyofbibtex")

    def test_dedup_by_doi(self):
        text = """
        @article{a, author={A}, title={One}, journal={J}, year={2020}, doi={10.1/x}}
        @article{b, author={A}, title={Two}, journal={J}, year={2021}, doi={https://doi.org/10.1/X}}
        """
        unique, removed = dedup_entries(parse(text))
        self.assertEqual([e.key for e in unique], ["a"])
        self.assertEqual(len(removed), 1)
        self.assertIn("DOI", removed[0][1])

    def test_dedup_by_title(self):
        text = """
        @article{a, author={A}, title={Same Title!}, journal={J}, year={2020}}
        @misc{b, author={B}, title={same title}, year={2021}}
        @article{c, author={C}, title={Different}, journal={J}, year={2022}}
        """
        unique, removed = dedup_entries(parse(text))
        self.assertEqual([e.key for e in unique], ["a", "c"])
        self.assertEqual(len(removed), 1)
        self.assertIn("title", removed[0][1])


class TestFormat(unittest.TestCase):
    def test_format_field_order_and_indent(self):
        entries = parse(
            "@article{k, year={2020}, title={T}, author={A}, journal={J}, volume={3}}"
        )
        out = format_entry(entries[0])
        lines = out.splitlines()
        self.assertEqual(lines[0], "@article{k,")
        self.assertEqual(lines[1], "  author = {A},")
        self.assertEqual(lines[2], "  title = {T},")
        self.assertEqual(lines[3], "  journal = {J},")
        self.assertEqual(lines[4], "  year = {2020},")
        self.assertEqual(lines[5], "  volume = {3}")
        self.assertEqual(lines[6], "}")

    def test_format_roundtrip(self):
        entries = parse(SAMPLE)
        reparsed = parse(format_entries(entries))
        self.assertEqual(reparsed, entries)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.entries = parse(SAMPLE)

    def test_search_by_author(self):
        hits = search_entries(self.entries, author="knuth")
        self.assertEqual([e.key for e in hits], ["knuth1984"])

    def test_search_by_year(self):
        hits = search_entries(self.entries, year="2020")
        self.assertEqual([e.key for e in hits], ["smith2020"])

    def test_search_by_query_matches_title(self):
        hits = search_entries(self.entries, query="texbook")
        self.assertEqual([e.key for e in hits], ["knuth1984"])

    def test_search_no_match(self):
        self.assertEqual(search_entries(self.entries, author="nobody"), [])


if __name__ == "__main__":
    unittest.main()
