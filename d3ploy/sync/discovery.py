"""
File discovery for synchronization.
"""

from pathlib import Path
from typing import List


def discover_files(
    path: Path,
    excludes: List[str],
    gitignore: bool = False,
) -> List[Path]:
    """
    Recursively discover files to sync.

    Args:
        path: Root directory to search.
        excludes: List of exclude patterns.
        gitignore: Whether to respect .gitignore rules.

    Returns:
        List of files to sync.
    """
    # TODO: Implement in Phase 3.3
    raise NotImplementedError("File discovery will be implemented in Phase 3.3")


def get_file_hash(file: Path) -> str:
    """
    Calculate MD5 hash of file.

    Args:
        file: Path to file.

    Returns:
        Hex-encoded MD5 hash.
    """
    # TODO: Implement in Phase 3.3
    raise NotImplementedError("File hashing will be implemented in Phase 3.3")
