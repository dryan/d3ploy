"""
Configuration migration for version upgrades.
"""

import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

CURRENT_VERSION = 2


def migrate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate configuration from old version to new version.

    Args:
        config: Configuration dictionary.

    Returns:
        Migrated configuration dictionary.

    Raises:
        ValueError: If migration path is not supported.
    """
    # Determine version
    version = config.get("version", 0)

    if version > CURRENT_VERSION:
        raise ValueError(
            f"Config version {version} is newer than supported version {CURRENT_VERSION}"
        )

    if version == CURRENT_VERSION:
        return config

    # Migration logic
    migrated_config = config.copy()

    # 0 -> 1: Add version field
    if version == 0:
        migrated_config["version"] = 1
        version = 1

    # 1 -> 2: Rename "environments" to "targets"
    if version == 1:
        if "environments" in migrated_config:
            migrated_config["targets"] = migrated_config.pop("environments")
        migrated_config["version"] = 2
        version = 2

    return migrated_config


def needs_migration(config: Dict[str, Any]) -> bool:
    """
    Check if config needs migration.

    Args:
        config: Configuration dictionary.

    Returns:
        True if migration is needed.
    """
    version = config.get("version", 0)
    return version < CURRENT_VERSION


def save_migrated_config(config: Dict[str, Any], *, path: str) -> None:
    """
    Save migrated config to disk.

    Args:
        config: Migrated configuration dictionary.
        path: Path to config file.
    """
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")  # Add trailing newline


def get_migration_command(config_path: Optional[str] = None) -> str:
    """
    Get the command to run to migrate a config file.

    Args:
        config_path: Path to config file (default: .d3ploy.json).

    Returns:
        Command string to run.
    """
    path = config_path or ".d3ploy.json"
    return f"d3ploy --migrate-config {path}"
