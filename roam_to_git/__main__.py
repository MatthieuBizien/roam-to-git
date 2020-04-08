#!/usr/bin/env python3
import argparse
import asyncio
import tempfile
from pathlib import Path

import git
from dotenv import load_dotenv

from roam_to_git.fs import reset_git_directory, unzip_markdown_archive, \
    unzip_json_archive, commit_git_directory
from roam_to_git.scrapping import patch_pyppeteer, download_rr_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=None,
                        help="Directory of your notes are stored. Default to notes/")
    parser.add_argument("--debug", action="store_true",
                        help="Help debug by opening the browser in the foreground. Note that the "
                             "git repository will not be updated with that option.")
    args = parser.parse_args()

    load_dotenv()
    patch_pyppeteer()

    if args.directory is None:
        git_path = Path(__file__).parent.parent / "notes"
    else:
        git_path = Path(args.directory).absolute()

    assert not git.Repo(git_path).bare  # Fail fast if it's not a repo

    with tempfile.TemporaryDirectory() as markdown_zip_path, \
            tempfile.TemporaryDirectory() as json_zip_path:
        markdown_zip_path = Path(markdown_zip_path)
        json_zip_path = Path(json_zip_path)

        tasks = [download_rr_archive("markdown", markdown_zip_path, devtools=args.debug),
                 download_rr_archive("json", json_zip_path, devtools=args.debug)
                 ]
        if args.debug:
            for task in tasks:
                # Run sequentially for easier debugging
                asyncio.get_event_loop().run_until_complete(task)
            print("Exiting without updating the git repository, "
                  "because we can't get the downloads with the option --debug")
            return
        else:
            asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        reset_git_directory(git_path)
        unzip_markdown_archive(markdown_zip_path, git_path)
        unzip_json_archive(json_zip_path, git_path)
        commit_git_directory(git_path)


if __name__ == "__main__":
    main()
