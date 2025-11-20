"""
Utility functions for d3ploy.

This module contains shared utilities for file operations,
MIME type detection, and other common tasks.
"""

from .mimetypes import get_content_type
from .mimetypes import register_custom_types
from .paths import get_app_data_dir
from .paths import get_cache_dir
from .paths import get_log_dir
from .paths import get_temp_dir
from .paths import get_update_check_file

__all__ = [
    "register_custom_types",
    "get_content_type",
    "get_app_data_dir",
    "get_cache_dir",
    "get_log_dir",
    "get_temp_dir",
    "get_update_check_file",
]
