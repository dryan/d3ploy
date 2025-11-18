"""
Configuration migration for version upgrades.
"""

from typing import Any
from typing import Dict

CURRENT_VERSION = 1


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

    return migrated_config
