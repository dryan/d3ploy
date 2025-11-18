"""
MIME type detection utilities.
"""

from pathlib import Path
from typing import Optional


def register_custom_types():
    """
    Register custom MIME type mappings.

    Adds additional MIME types not in standard library.
    """
    # TODO: Implement in Phase 3.6
    raise NotImplementedError("Custom MIME types will be implemented in Phase 3.6")


def get_content_type(file: Path, charset: Optional[str] = None) -> str:
    """
    Get Content-Type header value for file.

    Args:
        file: File path.
        charset: Optional charset to append (e.g., "utf-8").

    Returns:
        Full Content-Type header value.
    """
    # TODO: Implement in Phase 3.6
    raise NotImplementedError("Content-Type detection will be implemented in Phase 3.6")
