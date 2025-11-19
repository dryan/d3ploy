"""
Tests for d3ploy.ui.app and d3ploy.ui.dialogs modules.
"""

from unittest.mock import MagicMock
from unittest.mock import patch

from d3ploy.ui import app
from d3ploy.ui import dialogs

# Tests for D3ployApp


def test_d3ploy_app_initialization():
    """Initialize D3ployApp with default settings."""
    application = app.D3ployApp()

    assert application.quiet is False
    assert application.console is not None


def test_d3ploy_app_quiet_mode():
    """Initialize D3ployApp in quiet mode."""
    application = app.D3ployApp(quiet=True)

    assert application.quiet is True


def test_d3ploy_app_run_sync():
    """Run sync operation through app."""
    application = app.D3ployApp()
    mock_sync_func = MagicMock(return_value="result")

    result = application.run_sync(mock_sync_func, "arg1", kwarg1="value1")

    assert result == "result"
    mock_sync_func.assert_called_once_with("arg1", kwarg1="value1", quiet=False)


def test_d3ploy_app_run_sync_quiet_mode():
    """Run sync with quiet mode enabled."""
    application = app.D3ployApp(quiet=True)
    mock_sync_func = MagicMock(return_value="result")

    application.run_sync(mock_sync_func)

    mock_sync_func.assert_called_once_with(quiet=True)


def test_d3ploy_app_run_sync_override_quiet():
    """Run sync with explicit quiet parameter."""
    application = app.D3ployApp(quiet=True)
    mock_sync_func = MagicMock()

    application.run_sync(mock_sync_func, quiet=False)

    # Explicit quiet parameter should not be overridden
    mock_sync_func.assert_called_once_with(quiet=False)


def test_d3ploy_app_run_sync_with_args_and_kwargs():
    """Run sync with multiple args and kwargs."""
    application = app.D3ployApp()
    mock_sync_func = MagicMock()

    application.run_sync(
        mock_sync_func,
        "arg1",
        "arg2",
        key1="value1",
        key2="value2",
    )

    mock_sync_func.assert_called_once_with(
        "arg1",
        "arg2",
        key1="value1",
        key2="value2",
        quiet=False,
    )


# Tests for confirm_delete


def test_confirm_delete_yes(monkeypatch):
    """User confirms file deletion."""
    with patch("d3ploy.ui.dialogs.Confirm.ask", return_value=True):
        result = dialogs.confirm_delete("/path/to/file.txt")

        assert result is True


def test_confirm_delete_no(monkeypatch):
    """User declines file deletion."""
    with patch("d3ploy.ui.dialogs.Confirm.ask", return_value=False):
        result = dialogs.confirm_delete("/path/to/file.txt")

        assert result is False


def test_confirm_delete_message():
    """confirm_delete shows correct prompt."""
    with patch("d3ploy.ui.dialogs.Confirm.ask") as mock_ask:
        mock_ask.return_value = True

        dialogs.confirm_delete("test.txt")

        mock_ask.assert_called_once()
        call_args = mock_ask.call_args
        assert "Remove test.txt?" in call_args[0][0]


def test_confirm_delete_default_no():
    """confirm_delete defaults to False."""
    with patch("d3ploy.ui.dialogs.Confirm.ask") as mock_ask:
        mock_ask.return_value = False

        dialogs.confirm_delete("file.txt")

        assert mock_ask.call_args[1]["default"] is False


# Tests for show_dialog


def test_show_dialog_returns_choice():
    """show_dialog returns user's choice."""
    with patch("d3ploy.ui.dialogs.Prompt.ask", return_value="option1"):
        result = dialogs.show_dialog(
            "Title",
            "Message",
            ["option1", "option2"],
        )

        assert result == "option1"


def test_show_dialog_with_default():
    """show_dialog passes default choice."""
    with patch("d3ploy.ui.dialogs.Prompt.ask") as mock_ask:
        mock_ask.return_value = "default"

        dialogs.show_dialog(
            "Title",
            "Message",
            ["option1", "option2"],
            default="default",
        )

        assert mock_ask.call_args[1]["default"] == "default"


def test_show_dialog_includes_title():
    """show_dialog includes title in prompt."""
    with patch("d3ploy.ui.dialogs.Prompt.ask") as mock_ask:
        mock_ask.return_value = "option1"

        dialogs.show_dialog("Test Title", "Message", ["option1"])

        prompt_text = mock_ask.call_args[0][0]
        assert "Test Title" in prompt_text


def test_show_dialog_includes_message():
    """show_dialog includes message in prompt."""
    with patch("d3ploy.ui.dialogs.Prompt.ask") as mock_ask:
        mock_ask.return_value = "option1"

        dialogs.show_dialog("Title", "Test Message", ["option1"])

        prompt_text = mock_ask.call_args[0][0]
        assert "Test Message" in prompt_text


def test_show_dialog_passes_choices():
    """show_dialog passes choices to Prompt."""
    with patch("d3ploy.ui.dialogs.Prompt.ask") as mock_ask:
        mock_ask.return_value = "choice1"

        choices = ["choice1", "choice2", "choice3"]
        dialogs.show_dialog("Title", "Message", choices)

        assert mock_ask.call_args[1]["choices"] == choices
