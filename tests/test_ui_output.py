"""
Tests for d3ploy.ui.output module.
"""

from unittest.mock import patch

import pytest

from d3ploy.ui import output

# Tests for display_message


def test_display_message_info():
    """Display info message."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Test message", level="info")

        mock_print.assert_called_once_with("Test message", style="white")


def test_display_message_warning():
    """Display warning message."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Warning", level="warning")

        mock_print.assert_called_once_with("Warning", style="yellow bold")


def test_display_message_error():
    """Display error message to stderr."""
    with patch.object(output.error_console, "print") as mock_print:
        output.display_message("Error", level="error")

        mock_print.assert_called_once_with("Error", style="red bold")


def test_display_message_success():
    """Display success message."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Success", level="success")

        mock_print.assert_called_once_with("Success", style="green bold")


def test_display_message_quiet_mode():
    """Quiet mode suppresses info messages."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Test", level="info", quiet=True)

        mock_print.assert_not_called()


def test_display_message_quiet_mode_shows_errors():
    """Quiet mode still shows error messages."""
    with patch.object(output.error_console, "print") as mock_print:
        output.display_message("Error", level="error", quiet=True)

        mock_print.assert_called_once()


def test_display_message_quiet_mode_shows_warnings():
    """Quiet mode still shows warning messages."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Warning", level="warning", quiet=True)

        mock_print.assert_called_once()


def test_display_message_unknown_level():
    """Unknown level uses default white style."""
    with patch.object(output.console, "print") as mock_print:
        output.display_message("Test", level="unknown")

        mock_print.assert_called_once_with("Test", style="white")


# Tests for display_error


def test_display_error_prints_and_exits():
    """display_error prints to stderr and exits."""
    with patch.object(output.error_console, "print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            output.display_error("Fatal error")

        assert exc_info.value.code == 1
        mock_print.assert_called_once_with("Fatal error", style="red bold")


def test_display_error_custom_exit_code():
    """display_error uses custom exit code."""
    with patch.object(output.error_console, "print"):
        with pytest.raises(SystemExit) as exc_info:
            output.display_error("Error", exit_code=42)

        assert exc_info.value.code == 42


# Tests for display_table


def test_display_table_basic():
    """Display table with data."""
    rows = [
        {"name": "file1.txt", "size": "100"},
        {"name": "file2.txt", "size": "200"},
    ]

    with patch.object(output.console, "print") as mock_print:
        output.display_table(rows)

        mock_print.assert_called_once()
        # Check that a Table was printed
        assert mock_print.call_args[0][0].__class__.__name__ == "Table"


def test_display_table_with_title():
    """Display table with title."""
    rows = [{"name": "test", "value": "123"}]

    with patch.object(output.console, "print") as mock_print:
        output.display_table(rows, title="Test Table")

        table = mock_print.call_args[0][0]
        assert table.title == "Test Table"


def test_display_table_with_columns():
    """Display table with specific columns."""
    rows = [{"name": "test", "value": "123", "extra": "ignored"}]

    with patch.object(output.console, "print") as mock_print:
        output.display_table(rows, columns=["name", "value"])

        mock_print.assert_called_once()


def test_display_table_quiet_mode():
    """Quiet mode suppresses table display."""
    rows = [{"name": "test"}]

    with patch.object(output.console, "print") as mock_print:
        output.display_table(rows, quiet=True)

        mock_print.assert_not_called()


def test_display_table_empty_rows():
    """Empty rows list doesn't print table."""
    with patch.object(output.console, "print") as mock_print:
        output.display_table([])

        mock_print.assert_not_called()


# Tests for display_panel


def test_display_panel_with_string():
    """Display panel with string content."""
    with patch.object(output.console, "print") as mock_print:
        output.display_panel("Test content")

        mock_print.assert_called_once()
        panel = mock_print.call_args[0][0]
        assert panel.__class__.__name__ == "Panel"


def test_display_panel_with_dict():
    """Display panel with dict content."""
    content = {"key1": "value1", "key2": "value2"}

    with patch.object(output.console, "print") as mock_print:
        output.display_panel(content)

        mock_print.assert_called_once()


def test_display_panel_with_title():
    """Display panel with title."""
    with patch.object(output.console, "print") as mock_print:
        output.display_panel("Content", title="Test Title")

        panel = mock_print.call_args[0][0]
        assert panel.title == "Test Title"


def test_display_panel_with_border_style():
    """Display panel with custom border style."""
    with patch.object(output.console, "print") as mock_print:
        output.display_panel("Content", border_style="red")

        panel = mock_print.call_args[0][0]
        assert panel.border_style == "red"


def test_display_panel_quiet_mode():
    """Quiet mode suppresses panel display."""
    with patch.object(output.console, "print") as mock_print:
        output.display_panel("Content", quiet=True)

        mock_print.assert_not_called()


# Tests for display_json


def test_display_json_with_dict():
    """Display JSON from dict."""
    data = {"key": "value", "number": 123}

    with patch.object(output.console, "print") as mock_print:
        output.display_json(data)

        mock_print.assert_called_once()


def test_display_json_with_string():
    """Display JSON from string."""
    json_str = '{"key": "value"}'

    with patch.object(output.console, "print") as mock_print:
        output.display_json(json_str)

        mock_print.assert_called_once()


def test_display_json_with_file(tmp_path):
    """Display JSON from file."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"key": "value"}')

    with patch.object(output.console, "print") as mock_print:
        output.display_json(json_file)

        mock_print.assert_called_once()


def test_display_json_with_title():
    """Display JSON with title."""
    data = {"key": "value"}

    with patch.object(output.console, "print") as mock_print:
        output.display_json(data, title="Test JSON")

        # With title, prints Panel containing Syntax
        panel = mock_print.call_args[0][0]
        assert panel.__class__.__name__ == "Panel"
        assert panel.title == "Test JSON"


def test_display_json_without_line_numbers():
    """Display JSON without line numbers."""
    data = {"key": "value"}

    with patch.object(output.console, "print") as mock_print:
        output.display_json(data, line_numbers=False)

        mock_print.assert_called_once()


def test_display_json_quiet_mode():
    """Quiet mode suppresses JSON display."""
    with patch.object(output.console, "print") as mock_print:
        output.display_json({"key": "value"}, quiet=True)

        mock_print.assert_not_called()


# Tests for display_config


def test_display_config():
    """Display config calls display_json."""
    config = {"version": 2, "targets": {}}

    with patch("d3ploy.ui.output.display_json") as mock_display_json:
        output.display_config(config)

        mock_display_json.assert_called_once_with(
            config, title="Configuration", quiet=False
        )


def test_display_config_quiet_mode():
    """Quiet mode suppresses display."""
    config = {"version": 2}

    with patch.object(output.console, "print") as mock_print:
        output.display_config(config, quiet=True)

        # display_config returns early when quiet=True
        mock_print.assert_not_called()


# Tests for _format_value


def test_format_value_bool_true():
    """Format boolean true value."""
    result = output._format_value(True)

    assert "green" in result
    assert "true" in result


def test_format_value_bool_false():
    """Format boolean false value."""
    result = output._format_value(False)

    assert "red" in result
    assert "false" in result


def test_format_value_list():
    """Format list value."""
    result = output._format_value(["item1", "item2"])

    assert "item1" in result
    assert "item2" in result


def test_format_value_empty_list():
    """Format empty list."""
    result = output._format_value([])

    assert "[]" in result


def test_format_value_tuple():
    """Format tuple value."""
    result = output._format_value(("a", "b"))

    assert "a" in result
    assert "b" in result


def test_format_value_none():
    """Format None value."""
    result = output._format_value(None)

    assert "null" in result


def test_format_value_string():
    """Format string value."""
    result = output._format_value("test")

    assert "test" in result


def test_format_value_number():
    """Format number value."""
    result = output._format_value(42)

    assert "42" in result


# Tests for display_config_tree


def test_display_config_tree_basic():
    """Display config tree."""
    config = {
        "version": 2,
        "targets": {"production": {"bucket_name": "my-bucket"}},
        "defaults": {"acl": "private"},
    }

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config)

        mock_print.assert_called_once()
        panel = mock_print.call_args[0][0]
        assert panel.__class__.__name__ == "Panel"


def test_display_config_tree_with_title():
    """Display config tree with custom title."""
    config = {"version": 2, "targets": {}}

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config, title="Custom Title")

        panel = mock_print.call_args[0][0]
        assert panel.title == "Custom Title"


def test_display_config_tree_multiple_targets():
    """Display config tree with multiple targets."""
    config = {
        "version": 2,
        "targets": {
            "staging": {"bucket_name": "staging"},
            "production": {"bucket_name": "prod"},
        },
    }

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config)

        mock_print.assert_called_once()


def test_display_config_tree_merged_defaults():
    """Display config tree merges defaults with targets."""
    config = {
        "version": 2,
        "targets": {"prod": {"bucket_name": "my-bucket"}},
        "defaults": {"acl": "private", "processes": 4},
    }

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config)

        # Check that panel content includes both target-specific and default values
        panel = mock_print.call_args[0][0]
        content = str(panel.renderable)
        assert "bucket_name" in content
        assert "acl" in content
        assert "processes" in content


def test_display_config_tree_quiet_mode():
    """Quiet mode suppresses config tree display."""
    config = {"version": 2, "targets": {}}

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config, quiet=True)

        mock_print.assert_not_called()


def test_display_config_tree_empty_targets():
    """Display config tree with no targets."""
    config = {"version": 2, "targets": {}, "defaults": {"acl": "private"}}

    with patch.object(output.console, "print") as mock_print:
        output.display_config_tree(config)

        mock_print.assert_called_once()
