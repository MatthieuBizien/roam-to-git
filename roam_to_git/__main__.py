#!/usr/bin/env python3
import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import git
from dotenv import load_dotenv
from loguru import logger

from roam_to_git.formatter import read_markdown_directory, format_markdown
from roam_to_git.fs import reset_git_directory, save_files, unzip_and_save_archive, \
    commit_git_directory, push_git_repository
from roam_to_git.scrapping import patch_pyppeteer, scrap, Config, ROAM_FORMATS

CUSTOM_FORMATS = ("formatted",)
ALL_FORMATS = ROAM_FORMATS + CUSTOM_FORMATS
DEFAULT_FORMATS = ROAM_FORMATS[:2] + CUSTOM_FORMATS  # exclude EDN from default formats


# https://stackoverflow.com/a/41153081/3262054
# Extend action is only available in Python 3.8+
class ExtendAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest) or []
        items.extend(values)
        setattr(namespace, self.dest, items)


@logger.catch(reraise=True)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", default=None, nargs="?",
                        help="Directory of your notes are stored. Default to notes/")
    parser.add_argument("--debug", action="store_true",
                        help="Help debug by opening the browser in the foreground. Note that the "
                             "git repository will not be updated with that option.")
    parser.add_argument("--database", default=None,
                        help="If you have multiple Roam databases, select the one you want to save."
                             "Can also be configured with env variable ROAMRESEARCH_DATABASE.")
    parser.add_argument("--skip-git", action="store_true",
                        help="Consider the repository as just a directory, and don't do any "
                             "git-related action.")
    parser.add_argument("--skip-push", action="store_true",
                        help="Don't git push after commit.")
    parser.add_argument("--sleep-duration", type=float, default=2.,
                        help="Duration to wait for the interface. We wait 100x that duration for"
                             "Roam to load. Increase it if Roam servers are slow, but be careful"
                             "with the free tier of Github Actions.")
    parser.add_argument("--formats", "-f", action=ExtendAction, nargs="+", type=str,
                        help="Which formats to save. Options include json, markdown, formatted, "
                             "and edn. Note that if only formatted is specified, the markdown "
                             "directory will be converted to a formatted directory skipping "
                             "fetching entirely. Also note that if jet is installed, the edn "
                             "output will be pretty printed allowing for cleaner git diffs.")
    args = parser.parse_args()

    patch_pyppeteer()
    if args.directory is None:
        git_path = Path("notes").absolute()
    else:
        git_path = Path(args.directory).absolute()

    if (git_path / ".env").exists():
        logger.info("Loading secrets from {}", git_path / ".env")
        load_dotenv(git_path / ".env", override=True)
    else:
        logger.debug("No secret found at {}", git_path / ".env")
    if "ROAMRESEARCH_USER" not in os.environ or "ROAMRESEARCH_PASSWORD" not in os.environ:
        logger.error("Please define ROAMRESEARCH_USER and ROAMRESEARCH_PASSWORD, "
                     "in the .env file of your notes repository, or in environment variables")
        sys.exit(1)
    config = Config(args.database, debug=args.debug, sleep_duration=float(args.sleep_duration))

    if args.skip_git:
        repo = None
    else:
        repo = git.Repo(git_path)
        assert not repo.bare  # Fail fast if it's not a repo

    if args.formats is None or len(args.formats) == 0:
        args.formats = DEFAULT_FORMATS

    if any(f not in ALL_FORMATS for f in args.formats):
        logger.error("The format values must be one of {}.", ALL_FORMATS)
        sys.exit(1)

    # reset all directories to be modified
    for f in args.formats:
        reset_git_directory(git_path / f)

    # check if we need to fetch a format from roam
    roam_formats = [f for f in args.formats if f in ROAM_FORMATS]
    if len(roam_formats) > 0:
        with tempfile.TemporaryDirectory() as root_zip_path:
            root_zip_path = Path(root_zip_path)
            scrap(root_zip_path, roam_formats, config)
            if config.debug:
                logger.debug("waiting for the download...")
                time.sleep(20)
                return
            # Unzip and save all the downloaded files.
            for f in roam_formats:
                unzip_and_save_archive(f, root_zip_path / f, git_path / f)

    if "formatted" in args.formats:
        formatted = format_markdown(read_markdown_directory(git_path / "markdown"))
        save_files("formatted", git_path / "formatted", formatted)

    if repo is not None:
        commit_git_directory(repo)
        if not args.skip_push:
            push_git_repository(repo)


if __name__ == "__main__":
    main()
