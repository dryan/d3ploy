"""
Output formatting and display using Rich.
"""

import sys

from rich.console import Console

# Create console instances for different output streams
console = Console()
error_console = Console(stderr=True)


def display_message(
    text: str,
    *,
    level: str = "info",
    quiet: bool = False,
):
    """
    Display formatted message using Rich styling.

    Args:
        text: Message text.
        level: Message level (info, warning, error, success).
        quiet: Suppress output if True.
    """
    if quiet and level not in ["error", "warning"]:
        return

    style_map = {
        "info": "white",
        "warning": "yellow bold",
        "error": "red bold",
        "success": "green bold",
    }

    style = style_map.get(level, "white")
    target = error_console if level == "error" else console

    target.print(text, style=style)


def display_error(
    text: str,
    *,
    exit_code: int = 1,
):
    """
    Display error message and exit.

    Args:
        text: Error message.
        exit_code: Exit code for the program.
    """
    error_console.print(text, style="red bold")
    sys.exit(exit_code)
