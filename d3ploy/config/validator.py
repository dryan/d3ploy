"""
Configuration validation.
"""

from typing import Any
from typing import Dict

from .constants import RECOMMENDED_CACHES


def validate_config(data: Dict[str, Any]) -> Dict[str, Any]:
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

    # Check for environments
    if "environments" not in data:
        # It's possible to have a config with just defaults, but usually we want environments.
        raise ValueError("Configuration missing 'environments' key")

    if not isinstance(data["environments"], dict):
        raise ValueError("'environments' must be a dictionary")

    # Check defaults if present
    if "defaults" in data:
        if not isinstance(data["defaults"], dict):
            raise ValueError("'defaults' must be a dictionary")
        _expand_caches(data["defaults"])

    # Validate and expand environments
    for env_name, env_config in data["environments"].items():
        if not isinstance(env_config, dict):
            raise ValueError(f"Environment '{env_name}' must be a dictionary")
        _expand_caches(env_config)

    return data


def _expand_caches(config: Dict[str, Any]):
    """Expand 'caches': 'recommended' into actual values."""
    if config.get("caches") == "recommended":
        config["caches"] = RECOMMENDED_CACHES.copy()
