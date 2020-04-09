#!/usr/bin/env python3
import argparse
import asyncio
import os
import tempfile
from pathlib import Path

import git
from dotenv import load_dotenv

from roam_to_git.fs import reset_git_directory, unzip_markdown_archive, \
    unzip_json_archive, commit_git_directory, push_git_repository
from roam_to_git.scrapping import patch_pyppeteer, download_rr_archive


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=None,
                        help="Directory of your notes are stored. Default to notes/")
    parser.add_argument("--debug", action="store_true",
                        help="Help debug by opening the browser in the foreground. Note that the "
                             "git repository will not be updated with that option.")
    parser.add_argument("--database", default=os.environ.get("ROAMRESEARCH_DATABASE"),
                        help="If you have multiple Roam databases, select the one you want to save."
                             "Can also be configured with env variable ROAMRESEARCH_DATABASE.")
    parser.add_argument("--skip-git", action="store_true",
                        help="Consider the repository as just a directory, and don't do any "
                             "git-related action.")

    args = parser.parse_args()

    patch_pyppeteer()
    if args.directory is None:
        git_path = Path(__file__).parent.parent / "notes"
    else:
        git_path = Path(args.directory).absolute()

    if args.skip_git:
        repo = None
    else:
        repo = git.Repo(git_path)
        assert not repo.bare  # Fail fast if it's not a repo

    with tempfile.TemporaryDirectory() as markdown_zip_path, \
            tempfile.TemporaryDirectory() as json_zip_path:
        markdown_zip_path = Path(markdown_zip_path)
        json_zip_path = Path(json_zip_path)

        tasks = [download_rr_archive("markdown", markdown_zip_path, devtools=args.debug,
                                     database=args.database),
                 download_rr_archive("json", json_zip_path, devtools=args.debug,
                                     database=args.database),
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

    if repo is not None:
        commit_git_directory(repo)
        push_git_repository(repo)


if __name__ == "__main__":
    main()
