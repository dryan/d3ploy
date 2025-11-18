"""
User interface components for d3ploy using Textual.

This module provides both a full TUI interface (default) and
Rich-based CLI fallback for non-interactive environments.
"""

from .app import D3ployApp
from .dialogs import confirm_delete
from .output import display_error
from .output import display_message
from .progress import ProgressDisplay
from .tui import D3ployTUI
from .tui import run_tui

__all__ = [
    "D3ployApp",
    "D3ployTUI",
    "ProgressDisplay",
    "display_message",
    "display_error",
    "confirm_delete",
    "run_tui",
]
