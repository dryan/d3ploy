"""Tests for core CLI commands using Typer."""

import json
import os
import pathlib
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import typer

from d3ploy.config import CURRENT_VERSION
from d3ploy.core import cli as cli_module
from d3ploy.core.signals import UserCancelled

if TYPE_CHECKING:
    from collections.abc import Generator


class TestVersionCallback:
    """Tests for version callback."""

    def test_version_callback_shows_version(self) -> None:
        """Test that version callback displays version and exits."""
        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit):
                cli_module.version_callback(value=True)

            mock_print.assert_called_once()
            args = mock_print.call_args[0]
            assert "d3ploy" in args[0]
            # Version is from d3ploy module

    def test_version_callback_no_action_when_false(self) -> None:
        """Test that version callback does nothing when value is False."""
        result = cli_module.version_callback(value=False)
        assert result is None


class TestMainCallback:
    """Tests for main callback."""

    def test_main_callback_does_nothing(self) -> None:
        """Test that main callback just passes through."""
        result = cli_module.main(version=None)
        assert result is None


class TestSyncCommand:
    """Tests for sync command."""

    @pytest.fixture
    def mock_operations(self) -> "Generator[MagicMock, None, None]":
        """Mock sync operations."""
        with patch("d3ploy.core.cli.operations") as mock_ops:
            yield mock_ops

    @pytest.fixture
    def mock_signals(self) -> "Generator[MagicMock, None, None]":
        """Mock signal handlers."""
        with patch("d3ploy.core.cli.signals") as mock_sig:
            yield mock_sig

    @pytest.fixture
    def mock_updates(self) -> "Generator[MagicMock, None, None]":
        """Mock update checks."""
        with patch("d3ploy.core.cli.updates") as mock_upd:
            yield mock_upd

    @pytest.fixture
    def mock_ui(self) -> "Generator[MagicMock, None, None]":
        """Mock UI module."""
        with patch("d3ploy.core.cli.ui") as mock_ui:
            yield mock_ui

    @pytest.fixture
    def mock_config_path(self, *, tmp_path: pathlib.Path) -> pathlib.Path:
        """Create a mock config file."""
        config_file = tmp_path / "test-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "production": {
                    "bucket_name": "my-bucket",
                    "local_path": "./dist",
                    "bucket_path": "/",
                    "acl": "public-read",
                },
            },
            "defaults": {
                "charset": "utf-8",
            },
        }
        config_file.write_text(json.dumps(config_data))
        return config_file

    def test_sync_invalid_acl(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
    ) -> None:
        """Test that sync command rejects invalid ACL."""
        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit) as exc_info:
                cli_module.sync(acl="invalid-acl")

            assert exc_info.value.exit_code == os.EX_USAGE
            mock_print.assert_called_once()
            assert "Invalid ACL" in mock_print.call_args[0][0]

    def test_sync_with_valid_acl(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync command accepts valid ACL."""
        with patch("pathlib.Path.exists", return_value=False):
            cli_module.sync(
                targets=["production"],
                acl="public-read",
                bucket_name="test-bucket",
                config=str(mock_config_path),
            )

        # Should set up signals
        mock_signals.setup_signal_handlers.assert_called_once()

        # Should sync the target
        assert mock_operations.sync_target.called

    def test_sync_no_config_no_args_non_interactive(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_ui: MagicMock,
    ) -> None:
        """Test sync fails without config or args in non-interactive mode."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("sys.stdin.isatty", return_value=False):
                cli_module.sync(config="nonexistent.json")

        # Should display error
        mock_ui.output.display_error.assert_called_once()
        args = mock_ui.output.display_error.call_args[0]
        assert "No target specified" in args[0]

    @pytest.mark.timeout(5)
    def test_sync_with_old_deploy_json(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test sync detects old deploy.json file."""
        # Create an actual deploy.json file in tmp directory
        deploy_json = tmp_path / "deploy.json"
        deploy_json.write_text('{"old": "config"}')

        # Change to tmp directory for the test
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Mock stdin.isatty to prevent interactive prompts
            with patch("sys.stdin.isatty", return_value=False):
                # Run sync with bucket_name, non-default target, and ACL (to avoid prompts)
                cli_module.sync(
                    targets=["test"],
                    bucket_name="test-bucket",
                    acl="public-read",
                )

            # Should alert about old deploy.json
            mock_operations.alert.assert_called()
            calls = mock_operations.alert.call_args_list
            alert_messages = [call[0][0] for call in calls]
            assert any("deploy.json" in msg for msg in alert_messages)
        finally:
            os.chdir(original_cwd)

    def test_sync_loads_config_file(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync loads and uses config file."""
        cli_module.sync(
            targets=["production"],
            config=str(mock_config_path),
        )

        # Should sync the target with config values
        mock_operations.sync_target.assert_called_once()
        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["bucket_name"] == "my-bucket"
        assert call_kwargs["local_path"] == "./dist"
        assert call_kwargs["acl"] == "public-read"
        assert call_kwargs["charset"] == "utf-8"

    def test_sync_cli_args_override_config(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test that CLI arguments override config values."""
        cli_module.sync(
            targets=["production"],
            bucket_name="override-bucket",
            local_path="./override",
            acl="private",
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["bucket_name"] == "override-bucket"
        assert call_kwargs["local_path"] == "./override"
        assert call_kwargs["acl"] == "private"

    def test_sync_with_exclude_list(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with exclude patterns."""
        cli_module.sync(
            targets=["production"],
            exclude=["*.pyc", "__pycache__"],
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        excludes = call_kwargs["excludes"]
        assert "*.pyc" in excludes
        assert "__pycache__" in excludes
        # Config file should also be excluded
        assert str(mock_config_path) in excludes

    def test_sync_with_cloudfront_ids(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with CloudFront distribution IDs."""
        cli_module.sync(
            targets=["production"],
            cloudfront_id=["E1234567", "E7654321"],
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["cloudfront_id"] == ["E1234567", "E7654321"]

    def test_sync_with_force_flag(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with force flag to upload all files."""
        cli_module.sync(
            targets=["production"],
            force=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["force"] is True

    def test_sync_with_dry_run(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with dry run mode."""
        cli_module.sync(
            targets=["production"],
            dry_run=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["dry_run"] is True

    def test_sync_with_delete_flag(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with delete flag to remove orphaned files."""
        cli_module.sync(
            targets=["production"],
            delete=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["delete"] is True

    def test_sync_with_gitignore(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync respects gitignore patterns."""
        cli_module.sync(
            targets=["production"],
            gitignore=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["gitignore"] is True

    def test_sync_with_custom_processes(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with custom number of processes."""
        cli_module.sync(
            targets=["production"],
            processes=20,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["processes"] == 20

    def test_sync_all_targets(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test sync with --all flag syncs all targets."""
        config_file = tmp_path / "multi-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "staging": {"bucket_name": "staging-bucket"},
                "production": {"bucket_name": "prod-bucket"},
            },
        }
        config_file.write_text(json.dumps(config_data))

        cli_module.sync(
            all_targets=True,
            config=str(config_file),
        )

        # Should sync both targets
        assert mock_operations.sync_target.call_count == 2
        calls = mock_operations.sync_target.call_args_list
        synced_targets = [call[0][0] for call in calls]
        assert "staging" in synced_targets
        assert "production" in synced_targets

    def test_sync_with_quiet_flag(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with quiet flag suppresses output."""
        cli_module.sync(
            targets=["production"],
            quiet=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["quiet"] is True

    def test_sync_needs_migration(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_ui: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test sync detects config that needs migration."""
        config_file = tmp_path / "old-config.json"
        old_config = {
            "version": 0,
            "targets": {"default": {"bucket_name": "test"}},
        }
        config_file.write_text(json.dumps(old_config))

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.sync(config=str(config_file))

        assert exc_info.value.exit_code == os.EX_CONFIG
        # Should display migration message
        assert mock_ui.output.display_message.called

    def test_sync_invalid_target(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with non-existent target in config."""

        # Make alert raise typer.Exit to simulate sys.exit behavior
        def alert_side_effect(*args, **kwargs):
            if (
                kwargs.get("error_code") is not None
                and kwargs.get("error_code") != os.EX_OK
            ):
                raise typer.Exit(code=kwargs["error_code"])

        mock_operations.alert.side_effect = alert_side_effect

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.sync(
                targets=["nonexistent"],
                config=str(mock_config_path),
            )

        assert exc_info.value.exit_code == os.EX_NOINPUT

        # Should have alerted about invalid target
        mock_operations.alert.assert_called()
        # Find the alert call that mentions "not found in config"
        alert_calls = mock_operations.alert.call_args_list
        found_error = False
        for call in alert_calls:
            if "not found in config" in call[0][0]:
                found_error = True
                break
        assert found_error, "Expected alert about target not found in config"

    def test_sync_without_targets_in_config(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test sync with config that has no targets."""
        config_file = tmp_path / "empty-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {},
        }
        config_file.write_text(json.dumps(config_data))

        # Make alert raise typer.Exit to simulate sys.exit behavior
        def alert_side_effect(*args, **kwargs):
            if (
                kwargs.get("error_code") is not None
                and kwargs.get("error_code") != os.EX_OK
            ):
                raise typer.Exit(code=kwargs["error_code"])

        mock_operations.alert.side_effect = alert_side_effect

        # Need to provide a target to avoid the "No target specified" error
        # This test should check that empty targets in config is caught
        with pytest.raises(typer.Exit):
            cli_module.sync(targets=["any"], config=str(config_file))

        # Should have alerted about no targets
        mock_operations.alert.assert_called()
        alert_calls = mock_operations.alert.call_args_list
        found_error = False
        for call in alert_calls:
            if "No targets found" in call[0][0]:
                found_error = True
                break
        assert found_error, "Expected alert about no targets found"

    def test_sync_checks_for_updates(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync checks for updates."""
        cli_module.sync(
            targets=["production"],
            config=str(mock_config_path),
        )

        # Should check for updates
        from d3ploy import __version__

        mock_updates.check_for_updates.assert_called_once_with(__version__)

    def test_sync_update_check_exception_suppressed(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test that update check exceptions are suppressed."""
        mock_updates.check_for_updates.side_effect = Exception("Network error")

        # Ensure D3PLOY_DEBUG is not set
        with patch.dict(os.environ, {"D3PLOY_DEBUG": ""}, clear=False):
            # Should not raise exception
            cli_module.sync(
                targets=["production"],
                config=str(mock_config_path),
            )

        # Should still sync
        assert mock_operations.sync_target.called

    def test_sync_update_check_exception_raised_in_debug(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test that update check exceptions are raised in debug mode."""
        mock_updates.check_for_updates.side_effect = Exception("Network error")

        with patch.dict(os.environ, {"D3PLOY_DEBUG": "True"}):
            with pytest.raises(Exception, match="Network error"):
                cli_module.sync(
                    targets=["production"],
                    config=str(mock_config_path),
                )

    def test_sync_with_confirm_flag(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test sync with confirm flag for deletions."""
        cli_module.sync(
            targets=["production"],
            delete=True,
            confirm=True,
            config=str(mock_config_path),
        )

        call_kwargs = mock_operations.sync_target.call_args[1]
        assert call_kwargs["confirm"] is True

    def test_sync_interactive_target_selection(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test interactive target selection in terminal."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("d3ploy.ui.prompts.select_target") as mock_select:
                mock_select.return_value = "production"

                cli_module.sync(config=str(mock_config_path))

                # Should prompt for target
                mock_select.assert_called_once()
                # Should sync the selected target
                call_args = mock_operations.sync_target.call_args[0]
                assert call_args[0] == "production"

    def test_sync_interactive_target_selection_cancelled(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_config_path: pathlib.Path,
    ) -> None:
        """Test that cancelling target selection exits cleanly."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("d3ploy.ui.prompts.select_target") as mock_select:
                mock_select.return_value = None

                with pytest.raises(typer.Exit):
                    cli_module.sync(config=str(mock_config_path))

    def test_sync_interactive_bucket_config_prompt(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
    ) -> None:
        """Test interactive bucket config prompt when no config exists."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
                    mock_prompt.return_value = {
                        "bucket_name": "interactive-bucket",
                        "local_path": "./dist",
                        "bucket_path": "/",
                        "acl": "public-read",
                        "save_config": False,
                    }

                    cli_module.sync()

                    # Should prompt for bucket config
                    mock_prompt.assert_called_once()
                    # Should sync with prompted values
                    call_kwargs = mock_operations.sync_target.call_args[1]
                    assert call_kwargs["bucket_name"] == "interactive-bucket"

    def test_sync_interactive_bucket_config_cancelled(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
    ) -> None:
        """Test that cancelling bucket config prompt exits cleanly."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
                    mock_prompt.return_value = None

                    with pytest.raises(typer.Exit):
                        cli_module.sync()

    def test_sync_saves_config_when_requested(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        mock_ui: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test that config is saved when user requests it."""
        config_file = tmp_path / "new-config.json"

        with patch("sys.stdin.isatty", return_value=True):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
                    mock_prompt.return_value = {
                        "bucket_name": "new-bucket",
                        "local_path": "./dist",
                        "bucket_path": "/",
                        "acl": "public-read",
                        "save_config": True,
                        "caches": {"text/html": {"max-age": 3600}},
                    }

                    # Mock write_text to avoid actual file I/O
                    with patch.object(pathlib.Path, "write_text") as mock_write:
                        cli_module.sync(config=str(config_file))

                        # Should write config
                        assert mock_write.called
                        written_data = json.loads(mock_write.call_args[0][0])
                        assert written_data["version"] == CURRENT_VERSION
                        assert "new-bucket" in str(written_data)

    def test_sync_interactive_acl_prompt(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test interactive ACL prompt when not provided."""
        config_file = tmp_path / "no-acl-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "production": {
                    "bucket_name": "my-bucket",
                    "local_path": "./dist",
                },
            },
        }
        config_file.write_text(json.dumps(config_data))

        with patch("sys.stdin.isatty", return_value=True):
            with patch("d3ploy.ui.prompts.prompt_for_acl") as mock_acl:
                mock_acl.return_value = "private"

                cli_module.sync(
                    targets=["production"],
                    config=str(config_file),
                )

                # Should prompt for ACL
                mock_acl.assert_called_once()
                # Should use prompted ACL
                call_kwargs = mock_operations.sync_target.call_args[1]
                assert call_kwargs["acl"] == "private"

    def test_sync_multiple_targets_progress(
        self,
        mock_operations: MagicMock,
        mock_signals: MagicMock,
        mock_updates: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test that sync shows progress when syncing multiple targets."""
        config_file = tmp_path / "multi-targets.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "staging": {"bucket_name": "staging"},
                "production": {"bucket_name": "production"},
            },
        }
        config_file.write_text(json.dumps(config_data))

        cli_module.sync(
            targets=["staging", "production"],
            config=str(config_file),
        )

        # Should alert about progress
        alert_calls = mock_operations.alert.call_args_list
        progress_messages = [
            call[0][0] for call in alert_calls if "Uploading target" in call[0][0]
        ]
        assert len(progress_messages) == 2


class TestMigrateConfigCommand:
    """Tests for migrate-config command."""

    @pytest.fixture
    def old_config_file(self, *, tmp_path: pathlib.Path) -> pathlib.Path:
        """Create an old version config file."""
        config_file = tmp_path / "old-config.json"
        config_data = {
            "version": 0,
            "targets": {"default": {"bucket_name": "test-bucket"}},
        }
        config_file.write_text(json.dumps(config_data))
        return config_file

    @pytest.fixture
    def current_config_file(self, *, tmp_path: pathlib.Path) -> pathlib.Path:
        """Create a current version config file."""
        config_file = tmp_path / "current-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {"default": {"bucket_name": "test-bucket"}},
        }
        config_file.write_text(json.dumps(config_data))
        return config_file

    def test_migrate_config_file_not_found(self) -> None:
        """Test migrate_config with non-existent file."""
        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit) as exc_info:
                cli_module.migrate_config("nonexistent.json")

            assert exc_info.value.exit_code == os.EX_NOINPUT
            mock_print.assert_called_once()
            assert "Config file not found" in mock_print.call_args[0][0]

    def test_migrate_config_already_current(
        self, current_config_file: pathlib.Path
    ) -> None:
        """Test migrate_config with already current version."""
        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit):
                cli_module.migrate_config(str(current_config_file))

            # Should indicate it's already current
            assert mock_print.call_count >= 1
            # Find the call with "already at version" message
            found_message = False
            for call in mock_print.call_args_list:
                if "already at version" in call[0][0]:
                    found_message = True
                    break
            assert found_message, "Expected message about already at current version"

    def test_migrate_config_success(self, old_config_file: pathlib.Path) -> None:
        """Test successful config migration."""
        with patch.object(cli_module.console, "print") as mock_print:
            with patch("d3ploy.ui.display_panel") as mock_panel:
                cli_module.migrate_config(str(old_config_file))

                # Should show migration message
                assert any(
                    "Migrating config" in str(call)
                    for call in mock_print.call_args_list
                )
                # Should display panels (original and migrated)
                assert mock_panel.call_count == 2
                # Should show success message
                assert any(
                    "migrated successfully" in str(call)
                    for call in mock_print.call_args_list
                )

        # Verify file was migrated
        migrated_data = json.loads(old_config_file.read_text())
        assert migrated_data["version"] == CURRENT_VERSION

    def test_migrate_config_json_error(self, tmp_path: pathlib.Path) -> None:
        """Test migrate_config with invalid JSON."""
        bad_config = tmp_path / "bad-config.json"
        bad_config.write_text("not valid json {")

        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit) as exc_info:
                cli_module.migrate_config(str(bad_config))

            assert exc_info.value.exit_code == os.EX_DATAERR
            assert any(
                "Error migrating config" in str(call)
                for call in mock_print.call_args_list
            )


class TestShowConfigCommand:
    """Tests for show-config command."""

    @pytest.fixture
    def mock_config_file(self, *, tmp_path: pathlib.Path) -> pathlib.Path:
        """Create a mock config file."""
        config_file = tmp_path / "show-config.json"
        config_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "production": {
                    "bucket_name": "my-bucket",
                    "local_path": "./dist",
                },
            },
            "defaults": {"charset": "utf-8"},
        }
        config_file.write_text(json.dumps(config_data))
        return config_file

    def test_show_config_file_not_found(self) -> None:
        """Test show_config with non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.object(cli_module.console, "print") as mock_print:
                with pytest.raises(typer.Exit) as exc_info:
                    cli_module.show_config(config="nonexistent.json")

                assert exc_info.value.exit_code == os.EX_NOINPUT
                assert any(
                    "Config file not found" in str(call)
                    for call in mock_print.call_args_list
                )

    def test_show_config_tree_format(self, mock_config_file: pathlib.Path) -> None:
        """Test show_config displays tree format by default."""
        with patch("d3ploy.ui.display_config_tree") as mock_tree:
            cli_module.show_config(config=str(mock_config_file))

            mock_tree.assert_called_once()
            args = mock_tree.call_args
            config_data = args[0][0]
            assert config_data["version"] == CURRENT_VERSION
            assert "production" in config_data["targets"]

    def test_show_config_json_format(self, mock_config_file: pathlib.Path) -> None:
        """Test show_config displays JSON format when requested."""
        with patch("d3ploy.ui.display_json") as mock_json:
            cli_module.show_config(config=str(mock_config_file), json_format=True)

            mock_json.assert_called_once()
            args = mock_json.call_args
            config_data = args[0][0]
            assert config_data["version"] == CURRENT_VERSION

    def test_show_config_tries_alternate_location(self, tmp_path: pathlib.Path) -> None:
        """Test show_config tries .d3ploy.json if d3ploy.json not found."""
        alt_config = tmp_path / ".d3ploy.json"
        alt_config.write_text(json.dumps({"version": CURRENT_VERSION, "targets": {}}))

        # Use return_value instead of side_effect to avoid self parameter issues
        with patch("pathlib.Path.exists") as mock_exists:
            # Return False for d3ploy.json, True for .d3ploy.json
            mock_exists.return_value = False

            # Now we need to handle the second exists() call
            def exists_impl(*args, **kwargs):
                # First call (d3ploy.json) returns False, second call (.d3ploy.json) returns True
                if mock_exists.call_count <= 1:
                    return False
                return True

            mock_exists.side_effect = exists_impl

            with patch("pathlib.Path.read_text", return_value=alt_config.read_text()):
                with patch("d3ploy.ui.display_config_tree"):
                    cli_module.show_config()

    def test_show_config_invalid_json(self, tmp_path: pathlib.Path) -> None:
        """Test show_config with invalid JSON."""
        bad_config = tmp_path / "bad-config.json"
        bad_config.write_text("not valid json {")

        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit) as exc_info:
                cli_module.show_config(config=str(bad_config))

            assert exc_info.value.exit_code == os.EX_DATAERR
            assert any(
                "Invalid JSON" in str(call) for call in mock_print.call_args_list
            )

    def test_show_config_io_error(self, mock_config_file: pathlib.Path) -> None:
        """Test show_config handles I/O errors."""
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            with patch.object(cli_module.console, "print") as mock_print:
                with pytest.raises(typer.Exit) as exc_info:
                    cli_module.show_config(config=str(mock_config_file))

                assert exc_info.value.exit_code == os.EX_IOERR
                assert any(
                    "Error reading config" in str(call)
                    for call in mock_print.call_args_list
                )


class TestCreateConfigCommand:
    """Tests for create-config command."""

    def test_create_config_new_file(self, tmp_path: pathlib.Path) -> None:
        """Test create_config creates new config file."""
        config_file = tmp_path / "new-config.json"

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = {
                "bucket_name": "new-bucket",
                "local_path": "./dist",
                "bucket_path": "/",
                "acl": "public-read",
                "save_config": True,
            }

            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.write_text") as mock_write:
                    with patch.object(cli_module.console, "print"):
                        cli_module.create_config(config=str(config_file))

                    # Should write new config
                    assert mock_write.called
                    written_data = json.loads(mock_write.call_args[0][0])
                    assert written_data["version"] == CURRENT_VERSION
                    assert (
                        written_data["targets"]["default"]["bucket_name"]
                        == "new-bucket"
                    )

    def test_create_config_merge_existing(self, tmp_path: pathlib.Path) -> None:
        """Test create_config merges into existing file."""
        config_file = tmp_path / "existing-config.json"
        existing_data = {
            "version": CURRENT_VERSION,
            "targets": {
                "production": {"bucket_name": "prod-bucket"},
            },
        }
        config_file.write_text(json.dumps(existing_data))

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = {
                "bucket_name": "staging-bucket",
                "local_path": "./dist",
                "bucket_path": "/",
                "acl": "public-read",
                "save_config": True,
            }

            with patch("pathlib.Path.write_text") as mock_write:
                with patch.object(cli_module.console, "print"):
                    cli_module.create_config(config=str(config_file), target="staging")

                # Should merge new target
                written_data = json.loads(mock_write.call_args[0][0])
                assert "production" in written_data["targets"]
                assert "staging" in written_data["targets"]
                assert (
                    written_data["targets"]["staging"]["bucket_name"]
                    == "staging-bucket"
                )

    def test_create_config_cancelled(self, tmp_path: pathlib.Path) -> None:
        """Test create_config exits when user cancels."""
        config_file = tmp_path / "cancelled-config.json"

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = None

            with patch.object(cli_module.console, "print") as mock_print:
                with pytest.raises(typer.Exit):
                    cli_module.create_config(config=str(config_file))

                assert any(
                    "cancelled" in str(call).lower()
                    for call in mock_print.call_args_list
                )

    def test_create_config_with_caches(self, tmp_path: pathlib.Path) -> None:
        """Test create_config includes caches when provided."""
        config_file = tmp_path / "config-with-caches.json"

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = {
                "bucket_name": "bucket",
                "local_path": "./dist",
                "bucket_path": "/",
                "acl": "public-read",
                "caches": {"text/html": {"max-age": 3600}},
                "save_config": True,
            }

            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.write_text") as mock_write:
                    with patch.object(cli_module.console, "print"):
                        cli_module.create_config(config=str(config_file))

                    written_data = json.loads(mock_write.call_args[0][0])
                    assert "caches" in written_data["targets"]["default"]
                    assert (
                        written_data["targets"]["default"]["caches"]["text/html"][
                            "max-age"
                        ]
                        == 3600
                    )

    def test_create_config_without_saving(self, tmp_path: pathlib.Path) -> None:
        """Test create_config shows preview without saving."""
        config_file = tmp_path / "preview-config.json"

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = {
                "bucket_name": "bucket",
                "local_path": "./dist",
                "bucket_path": "/",
                "acl": "public-read",
                "save_config": False,
            }

            with patch("pathlib.Path.exists", return_value=False):
                with patch.object(cli_module.console, "print") as mock_print:
                    cli_module.create_config(config=str(config_file))

                    # Should show preview message
                    assert any(
                        "Preview" in str(call) for call in mock_print.call_args_list
                    )
                    assert any(
                        "not saved" in str(call).lower()
                        for call in mock_print.call_args_list
                    )

    def test_create_config_invalid_existing_json(self, tmp_path: pathlib.Path) -> None:
        """Test create_config exits on invalid existing JSON."""
        bad_config = tmp_path / "bad-config.json"
        bad_config.write_text("not valid json {")

        with patch.object(cli_module.console, "print") as mock_print:
            with pytest.raises(typer.Exit) as exc_info:
                cli_module.create_config(config=str(bad_config))

            assert exc_info.value.exit_code == os.EX_DATAERR
            assert any(
                "not valid JSON" in str(call) for call in mock_print.call_args_list
            )

    def test_create_config_checks_alternate_path(self, tmp_path: pathlib.Path) -> None:
        """Test create_config checks alternate config path."""
        alt_config = tmp_path / ".d3ploy.json"
        alt_config.write_text(
            json.dumps(
                {
                    "version": CURRENT_VERSION,
                    "targets": {"existing": {"bucket_name": "test"}},
                }
            )
        )

        with patch("d3ploy.ui.prompts.prompt_for_bucket_config") as mock_prompt:
            mock_prompt.return_value = {
                "bucket_name": "new",
                "local_path": ".",
                "bucket_path": "/",
                "acl": "private",
                "save_config": True,
            }

            with patch("pathlib.Path.read_text", return_value=alt_config.read_text()):
                with patch("pathlib.Path.write_text") as mock_write:
                    # Call with the alternate path directly
                    cli_module.create_config(config=str(alt_config))

                    # Should have written the merged config
                    assert mock_write.called


class TestCliEntryPoint:
    """Tests for cli() entry point function."""

    def test_cli_defaults_to_sync_command(self) -> None:
        """Test that cli() defaults to sync command when no subcommand given."""
        with patch("sys.argv", ["d3ploy", "production"]):
            with patch.object(cli_module, "app") as mock_app:
                cli_module.cli()

                # Should have inserted 'sync' command
                assert sys.argv[1] == "sync"
                assert sys.argv[2] == "production"
                mock_app.assert_called_once()

    def test_cli_preserves_explicit_subcommands(self) -> None:
        """Test that cli() doesn't modify explicit subcommands."""
        with patch("sys.argv", ["d3ploy", "show-config"]):
            with patch.object(cli_module, "app") as mock_app:
                cli_module.cli()

                # Should not insert 'sync'
                assert sys.argv[1] == "show-config"
                mock_app.assert_called_once()

    def test_cli_handles_flags(self) -> None:
        """Test that cli() doesn't insert sync before flags."""
        with patch("sys.argv", ["d3ploy", "--version"]):
            with patch.object(cli_module, "app") as mock_app:
                cli_module.cli()

                # Should not insert 'sync' before flags
                assert sys.argv[1] == "--version"
                mock_app.assert_called_once()

    def test_cli_catches_user_cancelled(self) -> None:
        """Test that cli() catches UserCancelled and exits cleanly."""
        with patch("sys.argv", ["d3ploy", "sync"]):
            with patch.object(cli_module, "app", side_effect=UserCancelled()):
                with patch.object(cli_module.console, "print") as mock_print:
                    with pytest.raises(SystemExit) as exc_info:
                        cli_module.cli()

                    assert exc_info.value.code == os.EX_OK
                    assert any(
                        "cancelled" in str(call).lower()
                        for call in mock_print.call_args_list
                    )

    def test_cli_no_args_defaults_to_sync(self) -> None:
        """Test that cli() with no args adds sync command."""
        with patch("sys.argv", ["d3ploy"]):
            with patch.object(cli_module, "app") as mock_app:
                cli_module.cli()

                # Should insert 'sync' as default command
                assert sys.argv[1] == "sync"
                mock_app.assert_called_once()
