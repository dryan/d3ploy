"""
Configuration validation.
"""

from typing import Any

from .constants import RECOMMENDED_CACHES


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and parse configuration structure.
    Also expands 'recommended' presets.

    Args:
        data: Raw configuration dictionary.

    Returns:
        Validated configuration object (dict for now).

    Raises:
        ValueError: If configuration is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a dictionary")

    # Check for targets
    if "targets" not in data:
        # It's possible to have a config with just defaults, but usually we
        # want targets.
        raise ValueError("Configuration missing 'targets' key")

    if not isinstance(data["targets"], dict):
        raise ValueError("'targets' must be a dictionary")

    # Check defaults if present
    if "defaults" in data:
        if not isinstance(data["defaults"], dict):
            raise ValueError("'defaults' must be a dictionary")
        _expand_caches(data["defaults"])

    # Validate and expand targets
    for target_name, target_config in data["targets"].items():
        if not isinstance(target_config, dict):
            raise ValueError(f"Target '{target_name}' must be a dictionary")
        _expand_caches(target_config)

    return data


def _expand_caches(config: dict[str, Any]):
    """Expand 'caches': 'recommended' into actual values."""
    if config.get("caches") == "recommended":
        config["caches"] = RECOMMENDED_CACHES.copy()
