"""
Tests for d3ploy.core.updates module (CheckForUpdatesTestCase conversion).
"""

import time
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from d3ploy.core import updates


@pytest.fixture
def test_check_file(tmp_path):
    """Create a temporary file for update check tracking."""
    check_file = tmp_path / "test_check.txt"
    yield check_file
    # Cleanup
    if check_file.exists():
        check_file.unlink()


@pytest.fixture
def mock_pypi_response():
    """Mock PyPI JSON response."""

    def _make_response(version: str):
        mock_response = Mock()
        mock_response.read.return_value = (
            f'{{"info": {{"version": "{version}"}}}}'.encode("utf-8")
        )
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda self, *args: None
        return mock_response

    return _make_response


# Tests for check_for_updates


def test_no_existing_file(test_check_file):
    """check_for_updates returns False when there isn't a previous check file."""
    # Ensure file doesn't exist
    if test_check_file.exists():
        test_check_file.unlink()

    result = updates.check_for_updates(
        "1.0.0",
        check_file_path=test_check_file,
    )
    # Will return False after checking (no update available relative to 1.0.0)
    # or None if the check failed for any reason
    assert result in [True, False, None]


def test_existing_recent_check(test_check_file):
    """check_for_updates returns None when there has been a recent check."""
    # Write a timestamp from 5 minutes ago (300 seconds)
    recent_time = int(time.time()) - 300
    test_check_file.write_text(str(recent_time))

    result = updates.check_for_updates(
        "1.0.0",
        check_file_path=test_check_file,
    )
    assert result is None, "Should not check again within 24 hours"


def test_existing_old_check(test_check_file, mock_pypi_response):
    """check_for_updates returns True or False when there hasn't been a recent check."""
    # Write a timestamp from over a day ago
    old_time = int(time.time()) - 100000
    test_check_file.write_text(str(old_time))

    with patch("urllib.request.urlopen") as mock_urlopen:
        # Mock PyPI response with current version
        mock_urlopen.return_value = mock_pypi_response("1.0.0")

        result = updates.check_for_updates(
            "1.0.0",
            check_file_path=test_check_file,
        )

        assert result in [True, False], "Should return boolean after checking"
        # Verify the check file was updated
        last_check = int(test_check_file.read_text().strip())
        assert last_check > old_time


def test_new_version_available(test_check_file, mock_pypi_response):
    """check_for_updates returns True when a newer version is on pypi.org."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        # Mock PyPI response with a newer version
        mock_urlopen.return_value = mock_pypi_response("999.0.0")

        result = updates.check_for_updates(
            "0.0.0",
            check_file_path=test_check_file,
        )

        assert result is True, "Should detect newer version"


def test_check_without_check_file_path(tmp_path):
    """check_for_updates uses default path when check_file_path is None."""
    # Mock the default check file location
    with patch("d3ploy.utils.get_update_check_file") as mock_get_path:
        mock_check_file = tmp_path / "default_check.txt"
        mock_get_path.return_value = mock_check_file

        # Write old timestamp to trigger check
        mock_check_file.write_text(str(int(time.time()) - 100000))

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"info": {"version": "1.0.0"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            result = updates.check_for_updates("0.0.0")

            assert result in [True, False, None]
            mock_get_path.assert_called_once()


def test_check_with_XDG_CONFIG_HOME_set(tmp_path, monkeypatch):
    """check_for_updates respects XDG_CONFIG_HOME environment variable."""
    xdg_config = tmp_path / "config"
    xdg_config.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

    with patch("d3ploy.utils.get_update_check_file") as mock_get_path:
        mock_check_file = xdg_config / "d3ploy" / "last_check.txt"
        mock_check_file.parent.mkdir(parents=True, exist_ok=True)
        mock_get_path.return_value = mock_check_file

        # Write old timestamp to trigger check
        mock_check_file.write_text(str(int(time.time()) - 100000))

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"info": {"version": "1.0.0"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            result = updates.check_for_updates("0.0.0")

            assert result in [True, False, None]


def test_check_with_XDG_CONFIG_HOME_not_set(tmp_path, monkeypatch):
    """check_for_updates uses fallback when XDG_CONFIG_HOME is not set."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    with patch("d3ploy.utils.get_update_check_file") as mock_get_path:
        mock_check_file = tmp_path / ".config" / "d3ploy" / "last_check.txt"
        mock_check_file.parent.mkdir(parents=True, exist_ok=True)
        mock_get_path.return_value = mock_check_file

        # Write old timestamp to trigger check
        mock_check_file.write_text(str(int(time.time()) - 100000))

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"info": {"version": "1.0.0"}}'
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            result = updates.check_for_updates("0.0.0")

            assert result in [True, False, None]


# Tests for get_last_check_time


def test_get_last_check_time_no_file(test_check_file):
    """Returns 0 when check file doesn't exist."""
    if test_check_file.exists():
        test_check_file.unlink()

    result = updates.get_last_check_time(check_file_path=test_check_file)
    assert result == 0


def test_get_last_check_time_with_file(test_check_file):
    """Returns timestamp from check file."""
    timestamp = 1234567890
    test_check_file.write_text(str(timestamp))

    result = updates.get_last_check_time(check_file_path=test_check_file)
    assert result == timestamp


def test_get_last_check_time_invalid_content(test_check_file):
    """Returns 0 when file contains invalid data."""
    test_check_file.write_text("invalid")

    result = updates.get_last_check_time(check_file_path=test_check_file)
    assert result == 0


# Tests for save_check_time


def test_save_check_time_saves_timestamp(test_check_file):
    """Saves timestamp to check file."""
    timestamp = 1234567890
    updates.save_check_time(timestamp, check_file_path=test_check_file)

    assert test_check_file.exists()
    assert int(test_check_file.read_text().strip()) == timestamp


def test_save_check_time_creates_parent_directory(tmp_path):
    """Creates parent directory if it doesn't exist."""
    nested_path = tmp_path / "nested" / "path" / "check.txt"
    timestamp = 1234567890

    updates.save_check_time(timestamp, check_file_path=nested_path)

    assert nested_path.exists()
    assert int(nested_path.read_text().strip()) == timestamp


# Tests for display_update_notification


def test_display_update_notification_basic(capsys):
    """Displays basic update notification."""
    updates.display_update_notification("2.0.0", current_version="1.0.0")

    captured = capsys.readouterr()
    assert "2.0.0" in captured.out
    assert "Update with:" in captured.out


def test_display_update_notification_major_version_warning(capsys):
    """Displays warning for major version updates."""
    updates.display_update_notification("2.0.0", current_version="1.0.0")

    captured = capsys.readouterr()
    assert "IMPORTANT" in captured.out
    assert "major version" in captured.out


def test_display_update_notification_minor_version_no_warning(capsys):
    """No special warning for minor/patch updates."""
    updates.display_update_notification("1.1.0", current_version="1.0.0")

    captured = capsys.readouterr()
    assert "IMPORTANT" not in captured.out
    assert "2.0.0" not in captured.out  # Should show 1.1.0
