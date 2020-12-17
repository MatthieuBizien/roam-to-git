import datetime
import json
import platform
import zipfile
from pathlib import Path
from typing import Dict, List

import git
import pathvalidate
from loguru import logger


def get_zip_path(zip_dir_path: Path) -> Path:
    """Return the path to the single zip file in a directory, and fail if there is not one single
    zip file"""
    zip_files = list(zip_dir_path.iterdir())
    zip_files = [f for f in zip_files if f.name.endswith(".zip")]
    assert len(zip_files) == 1, (zip_files, zip_dir_path)
    zip_path, = zip_files
    return zip_path


def reset_git_directory(git_path: Path, skip=(".git",)):
    """Remove all files in a git directory"""
    to_remove: List[Path] = []
    for file in git_path.glob("**/*"):
        if any(skip_item in file.parts for skip_item in skip):
            continue
        to_remove.append(file)
    # Now we remove starting from the end to remove childs before parents
    to_remove = sorted(set(to_remove))[::-1]
    for file in to_remove:
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            if list(file.iterdir()):
                logger.debug("Impossible to remove directory {}", file)
            else:
                file.rmdir()


def unzip_markdown_archive(zip_dir_path: Path):
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        contents = {file.filename: zip_file.read(file.filename).decode()
                    for file in zip_file.infolist()
                    if not file.is_dir()}
    return contents


def save_markdowns(directory: Path, contents: Dict[str, str]):
    logger.debug("Saving markdown to {}", directory)
    # Format and write the markdown files
    for file_name, content in contents.items():
        dest = get_clean_path(directory, file_name)
        dest.parent.mkdir(parents=True, exist_ok=True)  # Needed if a new directory is used
        # We have to specify encoding because crontab on Mac don't use UTF-8
        # https://stackoverflow.com/questions/11735363/python3-unicodeencodeerror-crontab
        with dest.open("w", encoding="utf-8") as f:
            f.write(content)


def unzip_and_save_json_archive(zip_dir_path: Path, directory: Path):
    logger.debug("Saving json to {}", directory)
    directory.mkdir(exist_ok=True)
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        files = list(zip_file.namelist())
        for file_name in files:
            assert file_name.endswith(".json")
            content = json.loads(zip_file.read(file_name).decode())
            with open(directory / file_name, "w") as f:
                json.dump(content, f, sort_keys=True, indent=2, ensure_ascii=True)


def commit_git_directory(repo: git.Repo):
    """Add an automatic commit in a git directory if it has changed, and push it"""
    if not repo.is_dirty() and not repo.untracked_files:
        # No change, nothing to do
        return
    logger.debug("Committing git repository {}", repo.git_dir)
    repo.git.add(A=True)  # https://github.com/gitpython-developers/GitPython/issues/292
    repo.index.commit(f"Automatic commit {datetime.datetime.now().isoformat()}")


def push_git_repository(repo: git.Repo):
    logger.debug("Pushing to origin")
    origin = repo.remote(name='origin')
    origin.push()


def get_clean_path(directory: Path, file_name: str) -> Path:
    """Remove any special characters on the file name"""
    out = directory
    for name in file_name.split("/"):
        out = out / pathvalidate.sanitize_filename(name, platform=platform.system())
    return out
