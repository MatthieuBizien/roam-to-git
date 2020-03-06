#!/usr/bin/env python3
import unittest
from typing import List

from rr_download import format_link, extract_links


class TestFormatLinks(unittest.TestCase):
    def test_empty(self):
        self.assertEquals(format_link(""), "")

    def test_no_link(self):
        self.assertEquals(format_link("string"), "string")

    def test_one_link(self):
        self.assertEquals(format_link("string [[link]]."), "string [link](<link.md>).")

    def test_two_links(self):
        self.assertEquals(format_link("[[link]] [[other]]"),
                          "[link](<link.md>) [other](<other.md>)")


def _extract_links(string) -> List[str]:
    return [m.group(1) for m in extract_links(string)]


class TestExtractLinks(unittest.TestCase):
    def test_empty(self):
        self.assertEquals(_extract_links(""), [])

    def test_no_link(self):
        self.assertEquals(_extract_links("string"), [])

    def test_one_link(self):
        self.assertEquals(_extract_links("string [[link]]."), ["link"])

    def test_two_links(self):
        self.assertEquals(_extract_links("[[link]] [[other]]"), ["link", "other"])


if __name__ == "__main__":
    unittest.main()
