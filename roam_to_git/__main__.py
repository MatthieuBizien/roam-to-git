#!/usr/bin/env python3
import argparse
import os
import tempfile
from pathlib import Path

import git
from dotenv import load_dotenv

from roam_to_git.formatter import format_markdown_archive
from roam_to_git.fs import reset_git_directory, unzip_markdown_archive, \
    unzip_and_save_json_archive, commit_git_directory, push_git_repository, save_markdowns
from roam_to_git.scrapping import patch_pyppeteer, scrap


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
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Do not download the data from Roam, just update the formatting.")

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

    reset_git_directory(git_path / "formatted")
    if not args.skip_fetch:
        reset_git_directory(git_path / "json")
        reset_git_directory(git_path / "markdown")

        with tempfile.TemporaryDirectory() as markdown_zip_path, \
                tempfile.TemporaryDirectory() as json_zip_path:
            markdown_zip_path = Path(markdown_zip_path)
            json_zip_path = Path(json_zip_path)

            scrap(markdown_zip_path, json_zip_path, args.database, args.debug)
            raws = unzip_markdown_archive(markdown_zip_path)
            save_markdowns(git_path / "markdown", raws)
            unzip_and_save_json_archive(json_zip_path, git_path / "json")

    formatted = format_markdown_archive(git_path / "markdown")
    save_markdowns(git_path / "formatted", formatted)

    if repo is not None:
        commit_git_directory(repo)
        push_git_repository(repo)


if __name__ == "__main__":
    main()
