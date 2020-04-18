import os
import re
from collections import defaultdict
from itertools import takewhile
from pathlib import Path
from typing import List, Match, Tuple, Dict


def format_markdown_archive(raw_directory: Path) -> Dict[str, str]:
    contents = {}
    for file in raw_directory.iterdir():
        if not file.is_file():
            continue
        with file.open(encoding="utf-8") as f:
            content = file.read_text(encoding="utf-8")
        parts = file.parts[len(raw_directory.parts):]
        file_name = os.path.join(*parts)
        contents[file_name] = content
    return format_markdown(contents)


def format_markdown(contents: Dict[str, str]) -> Dict[str, str]:
    # Extract backlinks from the markdown
    forward_links = {file_name: extract_links(content) for file_name, content in contents.items()}
    back_links: Dict[str, List[Tuple[str, Match]]] = defaultdict(list)
    for file_name, links in forward_links.items():
        for link in links:
            back_links[f"{link.group(1)}.md"].append((file_name, link))

    # Format and write the markdown files
    out = {}
    for file_name, content in contents.items():
        # We add the backlinks first, because they use the position of the caracters
        # of the regex matchs
        content = add_back_links(content, back_links[file_name])

        # Format content. Backlinks content will be formatted automatically.
        content = format_to_do(content)
        content = format_link(content)
        if len(content) > 0:
            out[file_name] = content

    return out


def format_to_do(contents: str):
    contents = re.sub(r"{{\[\[TODO\]\]}} *", r"[ ] ", contents)
    contents = re.sub(r"{{\[\[DONE\]\]}} *", r"[x] ", contents)
    return contents


def extract_links(string: str) -> List[Match]:
    out = list(re.finditer(r"\[\["
                           r"([^\]\n]+)"
                           r"\]\]", string))
    # Match attributes
    out.extend(re.finditer(r"(?:^|\n) *- "
                           r"((?:[^:\n]|:[^:\n])+)"  # Match everything except ::
                           r"::", string))
    return out


def add_back_links(content: str, back_links: List[Tuple[str, Match]]) -> str:
    if not back_links:
        return content
    files = sorted(set((file_name[:-3], match) for file_name, match in back_links),
                   key=lambda e: (e[0], e[1].start()))
    new_lines = []
    file_before = None
    for file, match in files:
        if file != file_before:
            new_lines.append(f"## [{file}](<{file}.md>)")
        file_before = file

        start_context_ = list(takewhile(lambda c: c != "\n", match.string[:match.start()][::-1]))
        start_context = "".join(start_context_[::-1])

        middle_context = match.string[match.start():match.end()]

        end_context_ = takewhile(lambda c: c != "\n", match.string[match.end()])
        end_context = "".join(end_context_)

        context = (start_context + middle_context + end_context).strip()
        new_lines.extend([context, ""])
    backlinks_str = "\n".join(new_lines)
    return f"{content}\n# Backlinks\n{backlinks_str}\n"


def format_link(string: str) -> str:
    """Transform a RoamResearch-like link to a Markdown link."""
    # Regex are read-only and can't parse [[[[recursive]] [[links]]]], but they do the job.
    # We use a special syntax for links that can have SPACES in them
    # Format internal reference: [[mynote]]
    string = re.sub(r"\[\["  # We start with [[
                    # TODO: manage a single ] in the tag
                    r"([^\]\n]+)"  # Everything except ]
                    r"\]\]",
                    r"[\1](<\1.md>)", string, flags=re.MULTILINE)

    # Format hashtags: #mytag
    string = re.sub(r"#([a-zA-Z-_0-9]+)", r"[\1](<\1.md>)", string, flags=re.MULTILINE)

    # Format attributes
    string = re.sub(r"(^ *- )"  # Match the beginning, like '  - '
                    r"(([^:\n]|:[^:\n])+)"  # Match everything except ::
                    r"::",
                    r"\1**[\2](<\2.md>):**",  # Format Markdown link
                    string, flags=re.MULTILINE)
    return string
