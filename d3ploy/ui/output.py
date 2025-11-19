"""
Output formatting and display using Rich.
"""

import json
import sys
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

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


def display_table(
    rows: List[Dict[str, Any]],
    *,
    title: Optional[str] = None,
    columns: Optional[List[str]] = None,
    quiet: bool = False,
):
    """
    Display data in a formatted table.

    Args:
        rows: List of dictionaries with data to display.
        title: Optional table title.
        columns: Optional list of column names to display (defaults to all keys).
        quiet: Suppress output if True.
    """
    if quiet or not rows:
        return

    # Get column names from first row if not specified
    if columns is None:
        columns = list(rows[0].keys())

    table = Table(title=title, show_header=True, header_style="bold cyan")

    # Add columns
    for col in columns:
        table.add_column(col, style="white")

    # Add rows
    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def display_panel(
    content: Union[str, Dict[str, Any]],
    *,
    title: Optional[str] = None,
    border_style: str = "blue",
    quiet: bool = False,
):
    """
    Display content in a styled panel.

    Args:
        content: Content to display (string or dict).
        title: Panel title.
        border_style: Border color/style.
        quiet: Suppress output if True.
    """
    if quiet:
        return

    # Convert dict to formatted string
    if isinstance(content, dict):
        content_str = "\n".join(
            f"[cyan]{key}:[/cyan] {value}" for key, value in content.items()
        )
    else:
        content_str = content

    panel = Panel(content_str, title=title, border_style=border_style)
    console.print(panel)


def display_json(
    data: Union[Dict[str, Any], str, Path],
    *,
    title: Optional[str] = None,
    line_numbers: bool = True,
    quiet: bool = False,
):
    """
    Display JSON data with syntax highlighting.

    Args:
        data: JSON data (dict, JSON string, or Path to JSON file).
        title: Optional title for display.
        line_numbers: Show line numbers.
        quiet: Suppress output if True.
    """
    if quiet:
        return

    # Convert data to JSON string
    if isinstance(data, Path):
        json_str = data.read_text()
    elif isinstance(data, dict):
        json_str = json.dumps(data, indent=2)
    else:
        json_str = data

    syntax = Syntax(
        json_str,
        "json",
        theme="monokai",
        line_numbers=line_numbers,
        word_wrap=True,
    )

    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def display_config(
    config: Dict[str, Any],
    *,
    quiet: bool = False,
):
    """
    Display configuration in a beautiful format.

    Args:
        config: Configuration dictionary.
        quiet: Suppress output if True.
    """
    if quiet:
        return

    display_json(config, title="Configuration", quiet=quiet)


def _format_value(value: Any) -> str:
    """
    Format a config value for display.

    Args:
        value: Value to format.

    Returns:
        Formatted string.
    """
    if isinstance(value, bool):
        return "[green]true[/green]" if value else "[red]false[/red]"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[dim][[]][/dim]"
        items = ", ".join(f"[yellow]{item}[/yellow]" for item in value)
        return f"[dim][[/dim]{items}[dim]][/dim]"
    if value is None:
        return "[dim]null[/dim]"
    return f"[yellow]{value}[/yellow]"


def display_config_tree(
    config: Dict[str, Any],
    *,
    title: Optional[str] = None,
    quiet: bool = False,
):
    """
    Display configuration in a tree-like format with defaults merged into targets.

    Args:
        config: Configuration dictionary.
        title: Optional title for the display.
        quiet: Suppress output if True.
    """
    if quiet:
        return

    version = config.get("version", 0)
    targets = config.get("targets", {})
    defaults = config.get("defaults", {})

    # Build the tree structure
    lines = []
    lines.append(f"[blue]Version:[/blue] [yellow]{version}[/yellow]")
    lines.append("")

    if targets:
        lines.append(f"[blue]Targets:[/blue] [dim]({len(targets)})[/dim]")
        target_items = list(targets.items())
        for idx, (target_name, target_config) in enumerate(target_items):
            is_last_target = idx == len(target_items) - 1
            target_prefix = "└──" if is_last_target else "├──"
            lines.append(f"{target_prefix} [cyan bold]{target_name}[/cyan bold]")

            # Merge defaults with target config
            merged_config = {**defaults, **target_config}
            config_items = list(merged_config.items())

            for config_idx, (key, value) in enumerate(config_items):
                is_last_item = config_idx == len(config_items) - 1
                item_prefix = "    └──" if is_last_target else "│   └──"
                if not is_last_item:
                    item_prefix = "    ├──" if is_last_target else "│   ├──"

                # Check if this is a default value or override
                is_default = key not in target_config
                key_style = "dim" if is_default else "white"
                formatted_value = _format_value(value)
                if is_default:
                    formatted_value = f"[dim]{formatted_value}[/dim]"

                lines.append(
                    f"{item_prefix} [{key_style}]{key}:[/{key_style}] {formatted_value}"
                )

    if defaults:
        lines.append("")
        lines.append("[blue]Defaults:[/blue]")
        default_items = list(defaults.items())
        for idx, (key, value) in enumerate(default_items):
            is_last = idx == len(default_items) - 1
            prefix = "└──" if is_last else "├──"
            formatted_value = _format_value(value)
            lines.append(f"{prefix} {key}: {formatted_value}")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title=title or "Configuration",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)
