import datetime
import json
import zipfile
from pathlib import Path

import git

from roam_to_git.formatter import format_markdown


def get_zip_path(zip_dir_path: Path) -> Path:
    """Return the path to the single zip file in a directory, and fail if there is not one single
    zip file"""
    zip_files = list(zip_dir_path.iterdir())
    zip_files = [f for f in zip_files if f.name.endswith(".zip")]
    assert len(zip_files) == 1, (zip_files, zip_dir_path)
    zip_path, = zip_files
    return zip_path


def reset_git_directory(git_path: Path):
    """Remove all files in a git directory"""
    for file in git_path.glob("**"):
        if not file.is_file():
            continue
        if ".git" in file.parts:
            continue
        file.unlink()


def unzip_markdown_archive(zip_dir_path: Path, git_path: Path):
    zip_path = get_zip_path(zip_dir_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        contents = {file.filename: zip_file.read(file.filename).decode()
                    for file in zip_file.infolist()
                    if not file.is_dir()}

    contents = format_markdown(contents)

    # Format and write the markdown files
    for file_name, content in contents.items():
        dest = (git_path / file_name)
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
