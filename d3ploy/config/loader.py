"""
Configuration file loading.
"""

from pathlib import Path
from typing import Optional


def load_config(path: Optional[Path] = None) -> dict:
    """
    Load configuration from d3ploy.json or .d3ploy.json.

    Args:
        path: Optional path to config file. If None, searches current directory.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If no config file is found.
        json.JSONDecodeError: If config file is invalid JSON.
    """
    # TODO: Implement in Phase 3.1
    raise NotImplementedError("Config loading will be implemented in Phase 3.1")
