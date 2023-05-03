import contextlib
import datetime
import json
import platform
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List
from subprocess import Popen, PIPE, STDOUT

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
    # Now we remove starting from the end to remove children before parents
    to_remove = sorted(set(to_remove))[::-1]
    for file in to_remove:
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            if list(file.iterdir()):
                logger.debug("Impossible to remove directory {}", file)
            else:
                file.rmdir()


def unzip_archive(zip_dir_path: Path):
    logger.debug("Unzipping {}", zip_dir_path)
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        contents = {file.filename: zip_file.read(file.filename).decode()
                    for file in zip_file.infolist()
                    if not file.is_dir()}
    return contents


def save_files(save_format: str, directory: Path, contents: Dict[str, str]):
    logger.debug("Saving {} to {}", save_format, directory)
    for file_name, content in contents.items():
        dest = get_clean_path(directory, file_name)
        dest.parent.mkdir(parents=True, exist_ok=True)  # Needed if a new directory is used
        # We have to specify encoding because crontab on Mac don't use UTF-8
        # https://stackoverflow.com/questions/11735363/python3-unicodeencodeerror-crontab
        with dest.open("w", encoding="utf-8") as f:
            if save_format == 'json':
                json.dump(json.loads(content), f, sort_keys=True, indent=2, ensure_ascii=True)
            else:  # markdown, formatted, edn
                if save_format == 'edn':
                    try:
                        jet = Popen(
                            ["jet", "--edn-reader-opts", "{:default tagged-literal}", "--pretty"],
                            stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                        jet_stdout, _ = jet.communicate(input=str.encode(content))
                        content = jet_stdout.decode()
                    except IOError:
                        logger.debug("Jet not installed, skipping EDN pretty printing")

                f.write(content)


def unzip_and_save_archive(save_format: str, zip_dir_path: Path, directory: Path):
    logger.debug("Saving {} to {}", save_format, directory)
    contents = unzip_archive(zip_dir_path)
    save_files(save_format, directory, contents)


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
        if name == "..":
            continue
        out = out / pathvalidate.sanitize_filename(name, platform=platform.system())
    return out


@contextlib.contextmanager
def create_temporary_directory(autodelete=True):
    if autodelete:
        with tempfile.TemporaryDirectory() as directory:
            yield directory
    else:
        now = datetime.datetime.now().isoformat().replace(":", "-")
        directory = Path("/tmp") / "roam-to-git" / now
        directory.mkdir(parents=True)
        yield directory
        # No clean-up
