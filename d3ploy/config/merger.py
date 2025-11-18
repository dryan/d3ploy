"""
Configuration merging logic.
"""

from typing import Any
from typing import Dict


def merge_config(
    defaults: Dict[str, Any],
    file_config: Dict[str, Any],
    env_config: Dict[str, Any],
    cli_args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge configuration from multiple sources with priority:
    CLI args > Env vars > File config > Defaults

    Args:
        defaults: Default values.
        file_config: Configuration from file (specific environment section).
        env_config: Configuration from environment variables.
        cli_args: Configuration from CLI arguments.

    Returns:
        Merged configuration dictionary.
    """
    merged = defaults.copy()

    # Update with file config
    merged.update({k: v for k, v in file_config.items() if v is not None})

    # Update with env config
    merged.update({k: v for k, v in env_config.items() if v is not None})

    # Update with CLI args
    merged.update({k: v for k, v in cli_args.items() if v is not None})

    return merged
