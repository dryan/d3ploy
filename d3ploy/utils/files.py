"""
File operation utilities.
"""

from pathlib import Path


def calculate_md5(file: Path) -> str:
    """
    Calculate MD5 hash of file.

    Args:
        file: Path to file.

    Returns:
        Hex-encoded MD5 hash string.
    """
    # TODO: Implement in Phase 3.6
    raise NotImplementedError("MD5 calculation will be implemented in Phase 3.6")


def format_size(bytes: int) -> str:
    """
    Format byte size as human-readable string.

    Args:
        bytes: Size in bytes.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    # TODO: Implement in Phase 3.6
    raise NotImplementedError("Size formatting will be implemented in Phase 3.6")


def normalize_path(path: Path) -> Path:
    """
    Normalize path separators for cross-platform compatibility.

    Args:
        path: Path to normalize.

    Returns:
        Normalized path.
    """
    # TODO: Implement in Phase 3.6
    raise NotImplementedError("Path normalization will be implemented in Phase 3.6")
