from rr_download import format_link


# Quick and dirty, Unittest in another day
def test_format_link():
    tests = [("", ""),
             ("string", "string"),
             ("string [[link]].", "string [link](<link.md>)."),
             ("[[link]] [[other]]", "[link](<link.md>) [other](<other.md>)"),
             ]
    for src, target in tests:
        transformed = format_link(src)
        assert transformed == target, (src, transformed, target)


if __name__ == "__main__":
    test_format_link()
