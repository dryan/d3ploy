"""
Version checking and update notifications.
"""

import contextlib
import json
import os
import pathlib
import time
import urllib.request
from typing import Optional
from typing import Union

from .. import utils


def check_for_updates(
    current_version: str,
    *,
    check_file_path: Optional[Union[pathlib.Path, str]] = None,
) -> Optional[bool]:
    """
    Check PyPI for newer version.

    Args:
        current_version: Current version string.
        check_file_path: Optional path to file tracking last check time.
                        If None, uses platform-specific app data directory.

    Returns:
        True if update available, False if up to date, None if check failed.
    """
    if check_file_path is None:
        check_file_path = utils.get_update_check_file()
    else:
        check_file_path = pathlib.Path(check_file_path).expanduser()

    if not check_file_path.exists():
        check_file_path.parent.mkdir(parents=True, exist_ok=True)
        check_file_path.touch()

    update_available = None

    try:
        from packaging.version import parse as parse_version
    except ImportError:
        return None

    PYPI_URL = "https://pypi.org/pypi/d3ploy/json"
    CHECK_FILE = pathlib.Path(check_file_path).expanduser()

    if not CHECK_FILE.exists():
        try:
            CHECK_FILE.write_text("")
        except IOError:
            pass

    try:
        last_checked = int(CHECK_FILE.read_text().strip())
    except ValueError:
        last_checked = 0

    now = int(time.time())

    if now - last_checked > 86400:
        if os.environ.get("D3PLOY_DEBUG"):
            print("checking for update")

        # it has been a day since the last update check
        try:
            with contextlib.closing(urllib.request.urlopen(PYPI_URL)) as pypi_response:
                pypi_data = json.load(pypi_response)
                pypi_version = parse_version(pypi_data.get("info", {}).get("version"))
                if pypi_version > parse_version(current_version):
                    display_update_notification(
                        str(pypi_version),
                        current_version=current_version,
                    )
                    update_available = True
                else:
                    update_available = False
        except ConnectionResetError:
            # if pypi fails, assume we can't get an update anyway
            update_available = False
        except Exception as e:
            if os.environ.get("D3PLOY_DEBUG"):
                raise e

        CHECK_FILE.write_text(str(now))

    return update_available


def display_update_notification(new_version: str, *, current_version: str = ""):
    """
    Display update available notification using Rich styling.

    Args:
        new_version: Version string of available update.
        current_version: Current version string for comparison.
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    message_lines = [
        f"[cyan]A new version of d3ploy is available:[/cyan] [green bold]{new_version}[/green bold]",
        "",
        "Update with: [yellow]pip install --upgrade d3ploy[/yellow]",
        "Or see: [blue]https://github.com/dryan/d3ploy[/blue]",
    ]

    # Check if this is a major version update
    is_major_update = False
    if current_version:
        try:
            from packaging.version import parse as parse_version

            current_major = parse_version(current_version).major
            new_major = parse_version(new_version).major
            is_major_update = new_major > current_major
        except Exception:
            pass

    if is_major_update:
        message_lines.extend(
            [
                "",
                "[yellow]⚠️  IMPORTANT:[/yellow] This is a major version update!",
                "[dim]Major updates may include breaking changes. Please review the",
                "changelog and migration guide at the GitHub repository before upgrading.[/dim]",
            ]
        )

    panel = Panel(
        "\n".join(message_lines),
        title="🎉 Update Available",
        border_style="yellow" if is_major_update else "cyan",
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()


def get_last_check_time(
    *,
    check_file_path: Optional[Union[pathlib.Path, str]] = None,
) -> int:
    """
    Get timestamp of last update check.

    Args:
        check_file_path: Optional path to check file.
                        If None, uses platform-specific app data directory.

    Returns:
        Unix timestamp of last check, or 0 if never checked.
    """
    if check_file_path is None:
        check_file_path = utils.get_update_check_file()
    else:
        check_file_path = pathlib.Path(check_file_path).expanduser()

    if not check_file_path.exists():
        return 0

    try:
        return int(check_file_path.read_text().strip())
    except ValueError:
        return 0


def save_check_time(
    timestamp: int,
    *,
    check_file_path: Optional[Union[pathlib.Path, str]] = None,
):
    """
    Save timestamp of update check.

    Args:
        timestamp: Unix timestamp to save.
        check_file_path: Optional path to check file.
                        If None, uses platform-specific app data directory.
    """
    if check_file_path is None:
        check_file_path = utils.get_update_check_file()
    else:
        check_file_path = pathlib.Path(check_file_path).expanduser()

    if not check_file_path.exists():
        check_file_path.parent.mkdir(parents=True, exist_ok=True)
        check_file_path.touch()

    check_file_path.write_text(str(timestamp))
