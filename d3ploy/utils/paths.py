"""
Platform-specific path utilities for d3ploy.

Provides standard app data directory paths following platform conventions:
- macOS: ~/Library/Application Support/d3ploy/
- Linux: $XDG_CONFIG_HOME/d3ploy/ or ~/.config/d3ploy/
- Windows: %APPDATA%\\d3ploy\\
"""

import os
import pathlib
import sys


def get_app_data_dir() -> pathlib.Path:
    """
    Get the platform-specific application data directory.

    Returns:
        Path to the app data directory (creates if doesn't exist).
    """
    if sys.platform == "darwin":
        # macOS: ~/Library/Application Support/d3ploy/
        base = pathlib.Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        # Windows: %APPDATA%\d3ploy\
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = pathlib.Path(appdata)
        else:
            base = pathlib.Path.home() / "AppData" / "Roaming"
    else:
        # Linux/Unix: $XDG_CONFIG_HOME/d3ploy/ or ~/.config/d3ploy/
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = pathlib.Path(xdg_config)
        else:
            base = pathlib.Path.home() / ".config"

    app_dir = base / "d3ploy"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_cache_dir() -> pathlib.Path:
    """
    Get the platform-specific cache directory.

    Returns:
        Path to the cache directory (creates if doesn't exist).
    """
    if sys.platform == "darwin":
        # macOS: ~/Library/Caches/d3ploy/
        base = pathlib.Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\d3ploy\Cache\
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = pathlib.Path(localappdata)
        else:
            base = pathlib.Path.home() / "AppData" / "Local"
        cache_dir = base / "d3ploy" / "Cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    else:
        # Linux/Unix: $XDG_CACHE_HOME/d3ploy/ or ~/.cache/d3ploy/
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        base = pathlib.Path(xdg_cache) if xdg_cache else pathlib.Path.home() / ".cache"

    cache_dir = base / "d3ploy"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_log_dir() -> pathlib.Path:
    """
    Get the platform-specific log directory.

    Returns:
        Path to the log directory (creates if doesn't exist).
    """
    if sys.platform == "darwin":
        # macOS: ~/Library/Logs/d3ploy/
        base = pathlib.Path.home() / "Library" / "Logs"
    elif sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\d3ploy\Logs\
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = pathlib.Path(localappdata)
        else:
            base = pathlib.Path.home() / "AppData" / "Local"
        log_dir = base / "d3ploy" / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    else:
        # Linux/Unix: $XDG_STATE_HOME/d3ploy/log/ or ~/.local/state/d3ploy/log/
        xdg_state = os.environ.get("XDG_STATE_HOME")
        if xdg_state:
            base = pathlib.Path(xdg_state)
        else:
            base = pathlib.Path.home() / ".local" / "state"
        log_dir = base / "d3ploy" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    log_dir = base / "d3ploy"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_temp_dir() -> pathlib.Path:
    """
    Get the platform-specific temporary directory.

    Returns:
        Path to the temp directory (creates if doesn't exist).
    """
    import tempfile

    # Use system temp directory with d3ploy subdirectory
    system_temp = pathlib.Path(tempfile.gettempdir())
    temp_dir = system_temp / "d3ploy"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_update_check_file() -> pathlib.Path:
    """
    Get the path to the update check timestamp file.

    Returns:
        Path to the last_check.txt file in the app data directory.
    """
    return get_app_data_dir() / "last_check.txt"
