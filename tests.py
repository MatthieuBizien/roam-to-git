#!/usr/bin/env python3
import unittest

from rr_download import format_link


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


if __name__ == "__main__":
    unittest.main()
