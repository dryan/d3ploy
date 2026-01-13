"""
Configuration file loading.
"""

import json
from pathlib import Path
from typing import Any

CONFIG_FILES = ["d3ploy.json", ".d3ploy.json"]


def load_config(path: str | None = None) -> dict[str, Any]:
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
    config_path = None

    if path:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
    else:
        # Search for default config files
        for filename in CONFIG_FILES:
            p = Path(filename)
            if p.exists():
                config_path = p
                break

    if not config_path:
        raise FileNotFoundError(
            f"No config file found. Looked for: {', '.join(CONFIG_FILES)}"
        )

    try:
        with Path(config_path).open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Error parsing {config_path}: {str(e)}", e.doc, e.pos
        ) from e
