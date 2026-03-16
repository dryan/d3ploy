"""
Tests for d3ploy.utils.paths module.
"""

import pathlib
import sys
from unittest.mock import patch

from d3ploy.utils import paths

# Tests for get_app_data_dir


def test_get_app_data_dir_macos(monkeypatch, tmp_path):
    """Get app data dir on macOS."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    app_dir = paths.get_app_data_dir()

    assert app_dir == tmp_path / "Library" / "Application Support" / "d3ploy"
    assert app_dir.exists()


def test_get_app_data_dir_windows_with_appdata(monkeypatch, tmp_path):
    """Get app data dir on Windows with APPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))

    app_dir = paths.get_app_data_dir()

    assert app_dir == tmp_path / "AppData" / "Roaming" / "d3ploy"
    assert app_dir.exists()


def test_get_app_data_dir_windows_without_appdata(monkeypatch, tmp_path):
    """Get app data dir on Windows without APPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    app_dir = paths.get_app_data_dir()

    assert app_dir == tmp_path / "AppData" / "Roaming" / "d3ploy"
    assert app_dir.exists()


def test_get_app_data_dir_linux_with_xdg(monkeypatch, tmp_path):
    """Get app data dir on Linux with XDG_CONFIG_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    app_dir = paths.get_app_data_dir()

    assert app_dir == tmp_path / "config" / "d3ploy"
    assert app_dir.exists()


def test_get_app_data_dir_linux_without_xdg(monkeypatch, tmp_path):
    """Get app data dir on Linux without XDG_CONFIG_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    app_dir = paths.get_app_data_dir()

    assert app_dir == tmp_path / ".config" / "d3ploy"
    assert app_dir.exists()


def test_get_app_data_dir_creates_directory(monkeypatch, tmp_path):
    """App data dir is created if it doesn't exist."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    app_dir = paths.get_app_data_dir()

    assert app_dir.exists()
    assert app_dir.is_dir()


# Tests for get_cache_dir


def test_get_cache_dir_macos(monkeypatch, tmp_path):
    """Get cache dir on macOS."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    cache_dir = paths.get_cache_dir()

    assert cache_dir == tmp_path / "Library" / "Caches" / "d3ploy"
    assert cache_dir.exists()


def test_get_cache_dir_windows_with_localappdata(monkeypatch, tmp_path):
    """Get cache dir on Windows with LOCALAPPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    cache_dir = paths.get_cache_dir()

    assert cache_dir == tmp_path / "AppData" / "Local" / "d3ploy" / "Cache"
    assert cache_dir.exists()


def test_get_cache_dir_windows_without_localappdata(monkeypatch, tmp_path):
    """Get cache dir on Windows without LOCALAPPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    cache_dir = paths.get_cache_dir()

    assert cache_dir == tmp_path / "AppData" / "Local" / "d3ploy" / "Cache"
    assert cache_dir.exists()


def test_get_cache_dir_linux_with_xdg(monkeypatch, tmp_path):
    """Get cache dir on Linux with XDG_CACHE_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    cache_dir = paths.get_cache_dir()

    assert cache_dir == tmp_path / "cache" / "d3ploy"
    assert cache_dir.exists()


def test_get_cache_dir_linux_without_xdg(monkeypatch, tmp_path):
    """Get cache dir on Linux without XDG_CACHE_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    cache_dir = paths.get_cache_dir()

    assert cache_dir == tmp_path / ".cache" / "d3ploy"
    assert cache_dir.exists()


# Tests for get_log_dir


def test_get_log_dir_macos(monkeypatch, tmp_path):
    """Get log dir on macOS."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    log_dir = paths.get_log_dir()

    assert log_dir == tmp_path / "Library" / "Logs" / "d3ploy"
    assert log_dir.exists()


def test_get_log_dir_windows_with_localappdata(monkeypatch, tmp_path):
    """Get log dir on Windows with LOCALAPPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    log_dir = paths.get_log_dir()

    assert log_dir == tmp_path / "AppData" / "Local" / "d3ploy" / "Logs"
    assert log_dir.exists()


def test_get_log_dir_windows_without_localappdata(monkeypatch, tmp_path):
    """Get log dir on Windows without LOCALAPPDATA."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    log_dir = paths.get_log_dir()

    assert log_dir == tmp_path / "AppData" / "Local" / "d3ploy" / "Logs"
    assert log_dir.exists()


def test_get_log_dir_linux_with_xdg(monkeypatch, tmp_path):
    """Get log dir on Linux with XDG_STATE_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    log_dir = paths.get_log_dir()

    assert log_dir == tmp_path / "state" / "d3ploy" / "log"
    assert log_dir.exists()


def test_get_log_dir_linux_without_xdg(monkeypatch, tmp_path):
    """Get log dir on Linux without XDG_STATE_HOME."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    log_dir = paths.get_log_dir()

    assert log_dir == tmp_path / ".local" / "state" / "d3ploy" / "log"
    assert log_dir.exists()


# Tests for get_temp_dir


def test_get_temp_dir(tmp_path, monkeypatch):
    """Get temp dir."""
    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        temp_dir = paths.get_temp_dir()

        assert temp_dir == tmp_path / "d3ploy"
        assert temp_dir.exists()


def test_get_temp_dir_creates_directory(tmp_path):
    """Temp dir is created if it doesn't exist."""
    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        temp_dir = paths.get_temp_dir()

        assert temp_dir.exists()
        assert temp_dir.is_dir()


# Tests for get_update_check_file


def test_get_update_check_file_returns_path(monkeypatch, tmp_path):
    """Get update check file path."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    check_file = paths.get_update_check_file()

    assert check_file == paths.get_app_data_dir() / "last_check.txt"
    assert check_file.parent.exists()


def test_get_update_check_file_in_app_data_dir(monkeypatch, tmp_path):
    """Update check file is in app data directory."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    check_file = paths.get_update_check_file()
    app_dir = paths.get_app_data_dir()

    assert check_file.parent == app_dir
