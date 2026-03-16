"""
Environment variable handling.
"""

import contextlib
import os
from typing import Any

PREFIX = "D3PLOY_"

ENV_MAPPING = {
    "BUCKET_NAME": "bucket_name",
    "LOCAL_PATH": "local_path",
    "BUCKET_PATH": "bucket_path",
    "ACL": "acl",
    "CHARSET": "charset",
    "PROCESSES": "processes",
}


def load_env_vars() -> dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Dictionary of configuration values from environment variables.
    """
    config = {}

    for env_key, config_key in ENV_MAPPING.items():
        full_key = f"{PREFIX}{env_key}"
        if full_key in os.environ:
            config[config_key] = os.environ[full_key]

    # Handle special cases or types if needed
    if f"{PREFIX}PROCESSES" in os.environ:
        with contextlib.suppress(ValueError):
            config["processes"] = int(os.environ[f"{PREFIX}PROCESSES"])

    return config
