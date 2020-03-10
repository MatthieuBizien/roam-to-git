#!/usr/bin/env python3
import unittest
from pathlib import Path
from typing import List

import mypy.api

from roam_to_git.formatter import format_to_do, extract_links, format_link


class TestFormatTodo(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_to_do(""), "")

    def test_no_link(self):
        self.assertEqual(format_to_do("string"), "string")

    def test_to_do(self):
        self.assertEqual(format_to_do("a\n- {{[[TODO]]}}string"), "a\n- [ ] string")

    def test_done(self):
        self.assertEqual(format_to_do("a\n- {{[[DONE]]}}string"), "a\n- [x] string")

    def test_something_else(self):
        self.assertEqual(format_to_do("a\n- {{[[ZZZ]]}}string"), "a\n- {{[[ZZZ]]}}string")


class TestFormatLinks(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_link(""), "")

    def test_no_link(self):
        self.assertEqual(format_link("string"), "string")

    def test_one_link(self):
        self.assertEqual(format_link("string [[link]]."), "string [link](<link.md>).")

    def test_two_links(self):
        self.assertEqual(format_link("[[link]] [[other]]"),
                         "[link](<link.md>) [other](<other.md>)")

    def test_one_hashtag(self):
        self.assertEqual(format_link("string #link."), "string [link](<link.md>).")

    def test_two_hashtag(self):
        self.assertEqual(format_link("#link #other"),
                         "[link](<link.md>) [other](<other.md>)")


def _extract_links(string) -> List[str]:
    return [m.group(1) for m in extract_links(string)]


class TestExtractLinks(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_extract_links(""), [])

    def test_no_link(self):
        self.assertEqual(_extract_links("string"), [])

    def test_one_link(self):
        self.assertEqual(_extract_links("string [[link]]."), ["link"])

    def test_two_links(self):
        self.assertEqual(_extract_links("[[link]] [[other]]"), ["link", "other"])

    def test_one_hashtag(self):
        self.assertEqual(_extract_links("string [[link]]."), ["link"])

    def test_two_hashtag(self):
        self.assertEqual(_extract_links("[[link]] [[other]]"), ["link", "other"])


class TestMypy(unittest.TestCase):
    def _test_mypy(self, files: List[str]):
        stdout, stderr, exit_status = mypy.api.run(["--ignore-missing-imports", *files])
        self.assertEqual(exit_status, 0)

    def test_mypy_rtg(self):
        self._test_mypy(["roam_to_git"])

    def test_mypy_rtg_and_tests(self):
        self._test_mypy(["roam_to_git", "tests.py"])

    def test_mypy_all(self):
        self._test_mypy([str(f) for f in Path(__file__).parent.iterdir()
                         if f.is_file() and f.name.endswith(".py")])


if __name__ == "__main__":
    unittest.main()
