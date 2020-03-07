#!/usr/bin/env python3

import asyncio
import datetime
import json
import os
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import List, Match, Tuple, Dict

import git
import pyppeteer.browser
from dotenv import load_dotenv


def patch_pyppeteer():
    """Fix https://github.com/miyakogi/pyppeteer/issues/178"""
    import pyppeteer.connection
    original_method = pyppeteer.connection.websockets.client.connect

    def new_method(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return original_method(*args, **kwargs)

    pyppeteer.connection.websockets.client.connect = new_method


patch_pyppeteer()


async def get_text(page, b, norm=True):
    """Get the inner text of an element"""
    text = await page.evaluate('(element) => element.textContent', b)
    if norm:
        text = text.lower().strip()
    return text


async def download_rr_archive(output_type: str,
                              output_directory: Path,
                              devtools=False,
                              sleep_duration=1.,
                              slow_motion=10):
    """Download an archive in RoamResearch.

    :param output_type: Download JSON or Markdown
    :param output_directory: Directory where to stock the outputs
    :param devtools: Should we open Chrome
    :param sleep_duration: How many seconds to wait after the clicks
    :param slow_motion: How many seconds to before to close the browser when the download is started
    """
    print("Creating browser")
    browser = await pyppeteer.launch(devtools=devtools, slowMo=slow_motion)
    document = await browser.newPage()

    if not devtools:
        print("Configure downloads to", output_directory)
        cdp = await document.target.createCDPSession()
        await cdp.send('Page.setDownloadBehavior',
                       {'behavior': 'allow', 'downloadPath': str(output_directory)})

    print("Opening signin page")
    await document.goto('https://roamresearch.com/#/signin')
    await asyncio.sleep(sleep_duration)

    print("Fill email")
    email_elem = await document.querySelector("input[name='email']")
    await email_elem.click()
    await email_elem.type(os.environ["ROAMRESEARCH_USER"])

    print("Fill password")
    passwd_elem = await document.querySelector("input[name='password']")
    await passwd_elem.click()
    await passwd_elem.type(os.environ["ROAMRESEARCH_PASSWORD"])

    print("Click on sign-in")
    buttons = await document.querySelectorAll('button')
    signin_confirm, = [b for b in buttons if await get_text(document, b) == 'sign in']
    await signin_confirm.click()
    await asyncio.sleep(sleep_duration)

    print("Wait for interface to load")
    dot_button = None
    for _ in range(100):
        # Starting is a little bit slow
        dot_button = await document.querySelector(".bp3-icon-more")
        if dot_button is None:
            await asyncio.sleep(sleep_duration)
        else:
            break
    await dot_button.click()

    print("Launch popup")
    divs_pb3 = await document.querySelectorAll(".bp3-fill")
    export_all, = [b for b in divs_pb3 if await get_text(document, b) == 'export all']
    await export_all.click()
    await asyncio.sleep(sleep_duration)

    async def get_dropdown_button():
        dropdown_button = await document.querySelector(".bp3-button-text")
        dropdown_button_text = await get_text(document, dropdown_button)
        # Defensive check if the interface change
        assert dropdown_button_text in ["markdown", "json"], dropdown_button_text
        return dropdown_button, dropdown_button_text

    print("Checking download type")
    button, button_text = await get_dropdown_button()

    if button_text != output_type:
        print("Changing output type to", output_type)
        await button.click()
        await asyncio.sleep(sleep_duration)
        output_type_elem, = await document.querySelectorAll(".bp3-text-overflow-ellipsis")
        await output_type_elem.click()

        # defensive check
        await asyncio.sleep(sleep_duration)
        _, button_text_ = await get_dropdown_button()
        assert button_text_ == output_type, (button_text_, output_type)

    print("Downloading output of type", output_type)
    buttons = await document.querySelectorAll('button')
    export_all_confirm, = [b for b in buttons if await get_text(document, b) == 'export all']
    await export_all_confirm.click()

    # Wait for download to finish
    if devtools:
        # No way to check because download location is not specified
        return
    for _ in range(1000):
        await asyncio.sleep(0.1)
        for file in output_directory.iterdir():
            if file.name.endswith(".zip"):
                print("File", file, "found")
                await asyncio.sleep(1)
                await browser.close()
                return
    await browser.close()
    raise FileNotFoundError(f"Impossible to download {output_type} in {output_directory}")


def get_zip_path(zip_dir_path: Path) -> Path:
    """Return the path to the single zip file in a directory, and fail if there is not one single
    zip file"""
    zip_dir_path = list(zip_dir_path.iterdir())
    zips_in_dir = [f for f in zip_dir_path if f.name.endswith(".zip")]
    assert len(zips_in_dir) == 1, (zips_in_dir, zip_dir_path)
    zip_path, = zips_in_dir
    return zip_path


def reset_git_directory(git_path: Path):
    """Remove all files in a git directory"""
    for file in git_path.glob("**"):
        if not file.is_file():
            continue
        if ".git" in file.parts:
            continue
        file.unlink()


def format_to_do(contents: str):
    contents = re.sub(r"{{\[\[TODO\]\]}} *", r"[ ] ", contents)
    contents = re.sub(r"{{\[\[DONE\]\]}} *", r"[x] ", contents)
    return contents


def extract_links(string: str) -> List[Match]:
    return list(re.finditer(r"\[\[([^\]]+)\]\]", string))


def add_backward_links(content: str, back_links: List[Tuple[str, Match]]) -> str:
    if not back_links:
        return content
    files = sorted(set(file_name[:-3] for file_name, matches in back_links))
    backlinks_str = "\n".join(f"- [{e}](<{e}.md>)" for e in files)
    return f"{content}\n# Backlinks\n{backlinks_str}\n"


def format_link(string: str) -> str:
    """Transform a RoamResearch-like link to a Markdown link."""
    # Regex are read-only and can't parse [[[[recursive]] [[links]]]], but they do the job.
    # We use a special syntax for links that can have SPACES in them
    return re.sub(r"\[\[([^\]]+)\]\]", r"[\1](<\1.md>)", string)


def unzip_markdown_archive(zip_dir_path: Path, git_path: Path):
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        contents = {file.filename: zip_file.read(file.filename).decode()
                    for file in zip_file.infolist()
                    if not file.is_dir()}

    # Extract backlinks from the markdown
    forward_links = {file_name: extract_links(content) for file_name, content in contents.items()}
    back_links: Dict[str, List[Tuple[str, Match]]] = defaultdict(list)
    for file_name, links in forward_links.items():
        for link in links:
            back_links[f"{link.group(1)}.md"].append((file_name, link))

    # Format and write the markdown files
    for file_name, content in contents.items():
        content = format_to_do(content)
        content = add_backward_links(content, back_links[file_name])
        content = format_link(content)
        dest = (git_path / file_name)
        if len(content) == 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)  # Needed if a new directory is used
        # We have to specify encoding because crontab on Mac don't use UTF-8
        # https://stackoverflow.com/questions/11735363/python3-unicodeencodeerror-crontab
        with dest.open("w", encoding="utf-8") as f:
            f.write(content)


def unzip_json_archive(zip_dir_path: Path, git_path: Path):
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        files = list(zip_file.namelist())
        for file in files:
            assert file.endswith(".json")
            content = json.loads(zip_file.read(file).decode())
            with open(git_path / file, "w") as f:
                json.dump(content, f, sort_keys=True, indent=2, ensure_ascii=True)


def commit_git_directory(git_path: Path):
    """Add an automatic commit in a git directory if it has changed, and push it"""
    repo = git.Repo(git_path)
    assert not repo.bare
    if not repo.is_dirty() and not repo.untracked_files:
        # No change, nothing to do
        return
    print("Committing in", git_path)
    repo.git.add(A=True)  # https://github.com/gitpython-developers/GitPython/issues/292
    repo.index.commit(f"Automatic commit {datetime.datetime.now().isoformat()}")

    print("Pushing to origin")
    origin = repo.remote(name='origin')
    origin.push()


def main():
    load_dotenv()

    git_path = Path(__file__).parent / "notes"  # FIXME use argparse

    with tempfile.TemporaryDirectory() as markdown_zip_path, \
            tempfile.TemporaryDirectory() as json_zip_path:
        markdown_zip_path = Path(markdown_zip_path)
        json_zip_path = Path(json_zip_path)

        tasks = [download_rr_archive("markdown", markdown_zip_path),
                 download_rr_archive("json", json_zip_path)]
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        reset_git_directory(git_path)
        unzip_markdown_archive(markdown_zip_path, git_path)
        unzip_json_archive(json_zip_path, git_path)
        commit_git_directory(git_path)


if __name__ == "__main__":
    main()
