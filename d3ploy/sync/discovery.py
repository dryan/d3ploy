"""
File discovery for synchronization.
"""

import hashlib
import os
import pathlib
from pathlib import Path
from typing import Collection
from typing import List
from typing import Union

import pathspec


def discover_files(
    local_path: Union[Path, str],
    *,
    excludes: Union[Collection[str], str, None] = None,
    gitignore: bool = False,
) -> List[Path]:
    """
    Recursively discover files to sync.

    Args:
        local_path: Root directory or file to search.
        excludes: List of exclude patterns.
        gitignore: Whether to respect .gitignore rules.

    Returns:
        List of files to sync.
    """
    if excludes is None:
        excludes = []
    if isinstance(excludes, str):
        excludes = [excludes]
    excludes = list(excludes)  # Make a copy
    excludes.append(".gitignore")

    if not isinstance(local_path, pathlib.Path):
        local_path = pathlib.Path(local_path)

    gitignore_patterns = list(map(pathspec.patterns.GitWildMatchPattern, excludes))
    svc_directories = [".git", ".svn"]

    if gitignore:
        gitignores = []
        if pathlib.Path(".gitignore").exists():
            gitignores.append(".gitignore")

        for root, dir_names, file_names in os.walk(local_path):
            for dir_name in dir_names:
                if dir_name in svc_directories:
                    continue
                dir_name = os.path.join(root, dir_name)
                gitignore_path = os.path.join(dir_name, ".gitignore")
                if os.path.exists(gitignore_path):
                    gitignores.append(gitignore_path)
            for file_name in file_names:
                if file_name == ".gitignore":
                    gitignore_path = os.path.join(root, file_name)
                    gitignores.append(gitignore_path)

        for gitignore_file in gitignores:
            with open(gitignore_file) as f:
                spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
                gitignore_patterns += [x for x in spec.patterns if x.regex]

    gitignore_spec = pathspec.PathSpec(gitignore_patterns)

    files = []
    if local_path.is_dir():
        for root, dir_names, file_names in os.walk(local_path):
            for file_name in file_names:
                file_name = pathlib.Path(root) / file_name
                if not gitignore_spec.match_file(file_name):
                    files.append(file_name)
            for svc_directory in svc_directories:
                if svc_directory in dir_names:
                    dir_names.remove(svc_directory)
    elif local_path.is_file() or local_path.is_symlink():
        if not gitignore_spec.match_file(local_path):
            files.append(local_path)

    return files


def get_file_hash(file: Path) -> str:
    """
    Calculate MD5 hash of file.

    Args:
        file: Path to file.

    Returns:
        Hex-encoded MD5 hash.
    """
    local_md5 = hashlib.md5()
    with open(file, "rb") as local_file:
        for chunk in iter(lambda: local_file.read(4096), b""):
            local_md5.update(chunk)
    return local_md5.hexdigest()
