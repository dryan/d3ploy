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

from ..compat import colorama


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

    Returns:
        True if update available, False if up to date, None if check failed.
    """
    if check_file_path is None:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            check_file_path = (
                pathlib.Path(xdg_config_home) / "d3ploy" / "last_check.txt"
            )
        else:
            check_file_path = pathlib.Path("~/.config/d3ploy/last_check.txt")
        check_file_path = check_file_path.expanduser()
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
                    display_update_notification(str(pypi_version))
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


def display_update_notification(new_version: str):
    """
    Display update available notification.

    Args:
        new_version: Version string of available update.
    """
    message = (
        f"There has been an update for d3ploy. Version "
        f"{new_version} is now available.\n"
        f"Please see https://github.com/dryan/d3ploy or run "
        f"`pip install --upgrade d3ploy`.\n\n"
        f"⚠️  IMPORTANT: A major update with breaking changes is coming soon! ⚠️\n"
        f"The next major version will include significant improvements but may\n"
        f"require config file updates. Please check the GitHub repository for\n"
        f"migration guidance before upgrading to version 5.0+."
    )
    print(f"{colorama.Fore.YELLOW}{message}{colorama.Style.RESET_ALL}")


def get_last_check_time(
    *,
    check_file_path: Optional[Union[pathlib.Path, str]] = None,
) -> int:
    """
    Get timestamp of last update check.

    Args:
        check_file_path: Optional path to check file.

    Returns:
        Unix timestamp of last check, or 0 if never checked.
    """
    if check_file_path is None:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            check_file_path = (
                pathlib.Path(xdg_config_home) / "d3ploy" / "last_check.txt"
            )
        else:
            check_file_path = pathlib.Path("~/.config/d3ploy/last_check.txt")
        check_file_path = check_file_path.expanduser()

    CHECK_FILE = pathlib.Path(check_file_path).expanduser()

    if not CHECK_FILE.exists():
        return 0

    try:
        return int(CHECK_FILE.read_text().strip())
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
    """
    if check_file_path is None:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            check_file_path = (
                pathlib.Path(xdg_config_home) / "d3ploy" / "last_check.txt"
            )
        else:
            check_file_path = pathlib.Path("~/.config/d3ploy/last_check.txt")
        check_file_path = check_file_path.expanduser()

    CHECK_FILE = pathlib.Path(check_file_path).expanduser()

    if not CHECK_FILE.exists():
        CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHECK_FILE.touch()

    CHECK_FILE.write_text(str(timestamp))
