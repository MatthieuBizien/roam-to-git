import re
from collections import defaultdict
from itertools import takewhile
from typing import List, Match, Tuple, Dict


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
        content = format_to_do(content)
        content = add_backward_links(content, back_links[file_name])
        content = format_link(content)
        if len(content) > 0:
            out[file_name] = content

    return out


def format_to_do(contents: str):
    contents = re.sub(r"{{\[\[TODO\]\]}} *", r"[ ] ", contents)
    contents = re.sub(r"{{\[\[DONE\]\]}} *", r"[x] ", contents)
    return contents


def extract_links(string: str) -> List[Match]:
    return list(re.finditer(r"\[\[([^\]]+)\]\]", string))


def add_backward_links(content: str, back_links: List[Tuple[str, Match]]) -> str:
    if not back_links:
        return content
    files = sorted(set((file_name[:-3], match) for file_name, match in back_links),
                   key=lambda e: (e[0], e[1].start()))
    new_lines = []
    for file, match in files:
        new_lines.append(f"## [{file}](<{file}.md>)")

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
    string = re.sub(r"\[\[([^\]]+)\]\]", r"[\1](<\1.md>)", string)
    string = re.sub(r"#([a-zA-Z-_0-9]+)", r"[\1](<\1.md>)", string)
    return string
