"""
File discovery for synchronization.
"""

import hashlib
import os
import pathlib
from pathlib import Path
from typing import Collection
from typing import List
from typing import Optional
from typing import Union

import pathspec

from .. import ui


def discover_files(
    local_path: Union[Path, str],
    *,
    excludes: Union[Collection[str], str, None] = None,
    gitignore: bool = False,
    config_file: Optional[Union[Path, str]] = None,
) -> List[Path]:
    """
    Recursively discover files to sync.

    Args:
        local_path: Root directory or file to search.
        excludes: List of exclude patterns for simple filename/glob matching.
        gitignore: Whether to respect .gitignore rules.
        config_file: Path to config file to automatically exclude.

    Returns:
        List of files to sync.
    """
    if excludes is None:
        excludes = []
    if isinstance(excludes, str):
        excludes = [excludes]
    excludes = list(excludes)  # Make a copy

    # Always exclude .gitignore files
    excludes.append(".gitignore")

    # Automatically exclude config file if provided
    if config_file:
        config_path = (
            Path(config_file) if not isinstance(config_file, Path) else config_file
        )
        excludes.append(config_path.name)

    if not isinstance(local_path, pathlib.Path):
        local_path = pathlib.Path(local_path)

    # Create pathspec for simple exclude patterns (not gitignore-style)
    exclude_spec = pathspec.PathSpec(
        list(map(pathspec.patterns.GitWildMatchPattern, excludes))
    )

    svc_directories = [".git", ".svn"]
    gitignore_patterns = []

    if gitignore:
        gitignores = []
        # Check for .gitignore in current directory
        if pathlib.Path(".gitignore").exists():
            gitignores.append(".gitignore")

        # Find all .gitignore files in the tree
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

        # Warn if gitignore requested but none found
        if not gitignores:
            ui.output.display_message(
                "gitignore requested but no .gitignore files were found",
                level="warning",
            )

        # Load patterns from all .gitignore files
        for gitignore_file in gitignores:
            with open(gitignore_file) as f:
                spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
                gitignore_patterns += [x for x in spec.patterns if x.regex]

    # Create combined spec for gitignore patterns (only if gitignore=True)
    gitignore_spec = (
        pathspec.PathSpec(gitignore_patterns) if gitignore_patterns else None
    )

    files = []
    if local_path.is_dir():
        for root, dir_names, file_names in os.walk(local_path):
            for file_name in file_names:
                file_path = pathlib.Path(root) / file_name

                # Check exclude patterns (simple globs)
                if exclude_spec.match_file(file_path):
                    continue

                # Check gitignore patterns if enabled
                if gitignore_spec and gitignore_spec.match_file(file_path):
                    continue

                files.append(file_path)

            # Remove service directories from traversal
            for svc_directory in svc_directories:
                if svc_directory in dir_names:
                    dir_names.remove(svc_directory)

    elif local_path.is_file() or local_path.is_symlink():
        # For single files, check exclude patterns
        if not exclude_spec.match_file(local_path):
            # Also check gitignore if enabled
            if gitignore_spec is None or not gitignore_spec.match_file(local_path):
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
