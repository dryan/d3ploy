"""
Tests for d3ploy.ui.prompts module.
"""

from unittest.mock import Mock
from unittest.mock import patch

from d3ploy.ui import prompts


class TestSelectTarget:
    """Tests for select_target function."""

    def test_select_target_with_valid_config(self, tmp_path):
        """Test selecting a target with valid config."""
        config_file = tmp_path / "d3ploy.json"
        config_file.write_text(
            '{"targets": {"prod": {"bucket_name": "my-bucket", "local_path": "."}}}'
        )

        with patch("questionary.select") as mock_select:
            mock_result = Mock()
            mock_result.ask.return_value = "prod"
            mock_select.return_value = mock_result

            result = prompts.select_target(config_path=str(config_file))

            assert result == "prod"
            mock_select.assert_called_once()

    def test_select_target_user_cancels(self, tmp_path):
        """Test when user cancels target selection."""
        config_file = tmp_path / "d3ploy.json"
        config_file.write_text(
            '{"targets": {"prod": {"bucket_name": "my-bucket", "local_path": "."}}}'
        )

        with patch("questionary.select") as mock_select:
            mock_result = Mock()
            mock_result.ask.return_value = None
            mock_select.return_value = mock_result

            result = prompts.select_target(config_path=str(config_file))

            assert result is None

    def test_select_target_no_targets_in_config(self, tmp_path):
        """Test when config has no targets."""
        config_file = tmp_path / "d3ploy.json"
        config_file.write_text('{"targets": {}}')

        result = prompts.select_target(config_path=str(config_file))

        assert result is None

    def test_select_target_config_load_error(self, tmp_path):
        """Test when config file cannot be loaded."""
        config_file = tmp_path / "nonexistent.json"

        result = prompts.select_target(config_path=str(config_file))

        assert result is None

    def test_select_target_invalid_json(self, tmp_path):
        """Test when config file contains invalid JSON."""
        config_file = tmp_path / "d3ploy.json"
        config_file.write_text("invalid json{}")

        result = prompts.select_target(config_path=str(config_file))

        assert result is None


class TestConfirmConfigMigration:
    """Tests for confirm_config_migration function."""

    def test_confirm_config_migration_user_confirms(self, tmp_path):
        """Test when user confirms migration."""
        config_file = tmp_path / "d3ploy.json"

        with patch("rich.prompt.Confirm.ask", return_value=True):
            result = prompts.confirm_config_migration(
                config_path=str(config_file),
                old_version=0,
                new_version=2,
            )

            assert result is True

    def test_confirm_config_migration_user_declines(self, tmp_path):
        """Test when user declines migration."""
        config_file = tmp_path / "d3ploy.json"

        with patch("rich.prompt.Confirm.ask", return_value=False):
            result = prompts.confirm_config_migration(
                config_path=str(config_file),
                old_version=0,
                new_version=2,
            )

            assert result is False


class TestPromptForBucketConfig:
    """Tests for prompt_for_bucket_config function."""

    def test_prompt_basic_config_existing_bucket(self):
        """Test prompting for config with existing bucket."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
            patch("d3ploy.aws.s3.list_buckets", return_value=["bucket1", "bucket2"]),
        ):
            # Set up mock responses
            select_results = [
                Mock(ask=Mock(return_value="existing")),  # Bucket choice
                Mock(ask=Mock(return_value="bucket1")),  # Select bucket
                Mock(ask=Mock(return_value="public-read")),  # ACL
            ]
            mock_select.side_effect = select_results

            mock_prompt.side_effect = [".", ""]  # local_path, bucket_path

            mock_confirm.side_effect = [False, True]  # cache, save_config

            result = prompts.prompt_for_bucket_config()

            assert result is not None
            assert result["bucket_name"] == "bucket1"
            assert result["local_path"] == "."
            assert result["bucket_path"] == ""
            assert result["acl"] == "public-read"
            assert result["save_config"] is True

    def test_prompt_basic_config_new_bucket(self):
        """Test prompting for config with new bucket."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
        ):
            # Set up mock responses
            select_results = [
                Mock(ask=Mock(return_value="new")),  # Bucket choice
                Mock(ask=Mock(return_value="public-read")),  # ACL
            ]
            mock_select.side_effect = select_results

            mock_prompt.side_effect = [
                "my-new-bucket",  # bucket_name
                ".",  # local_path
                "",  # bucket_path
            ]

            mock_confirm.side_effect = [False, True]  # cache, save_config

            result = prompts.prompt_for_bucket_config()

            assert result is not None
            assert result["bucket_name"] == "my-new-bucket"

    def test_prompt_with_checked_paths(self):
        """Test prompting with checked_paths parameter."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
        ):
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="new")),
                Mock(ask=Mock(return_value="public-read")),
            ]
            mock_prompt.side_effect = ["bucket", ".", ""]
            mock_confirm.side_effect = [False, True]

            result = prompts.prompt_for_bucket_config(
                checked_paths=["/path1/d3ploy.json", "/path2/d3ploy.json"]
            )

            assert result is not None

    def test_prompt_skip_no_config_message(self):
        """Test skipping the no config message."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
        ):
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="new")),
                Mock(ask=Mock(return_value="public-read")),
            ]
            mock_prompt.side_effect = ["bucket", ".", ""]
            mock_confirm.side_effect = [False, True]

            result = prompts.prompt_for_bucket_config(skip_no_config_message=True)

            assert result is not None

    def test_prompt_with_ask_confirmation_user_declines(self):
        """Test when ask_confirmation is True and user declines."""
        with patch("rich.prompt.Confirm.ask", return_value=False):
            result = prompts.prompt_for_bucket_config(ask_confirmation=True)

            assert result is None

    def test_prompt_with_ask_confirmation_user_accepts(self):
        """Test when ask_confirmation is True and user accepts."""
        with (
            patch("rich.prompt.Confirm.ask") as mock_confirm,
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False, True]  # confirm, cache, save
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="new")),
                Mock(ask=Mock(return_value="public-read")),
            ]
            mock_prompt.side_effect = ["bucket", ".", ""]

            result = prompts.prompt_for_bucket_config(ask_confirmation=True)

            assert result is not None

    def test_prompt_user_cancels_bucket_choice(self):
        """Test when user cancels at bucket choice."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value = Mock(ask=Mock(return_value=None))

            result = prompts.prompt_for_bucket_config()

            assert result is None

    def test_prompt_no_buckets_available(self):
        """Test when no buckets are available and user enters manually."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
            patch("d3ploy.aws.s3.list_buckets", return_value=[]),
        ):
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="existing")),  # Bucket choice
                Mock(ask=Mock(return_value="public-read")),  # ACL
            ]

            mock_prompt.side_effect = [
                "manual-bucket",  # bucket_name
                ".",  # local_path
                "",  # bucket_path
            ]

            mock_confirm.side_effect = [False, True]  # cache, save_config

            result = prompts.prompt_for_bucket_config()

            assert result is not None
            assert result["bucket_name"] == "manual-bucket"

    def test_prompt_manual_bucket_entry(self):
        """Test when user chooses to enter bucket name manually."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
            patch("d3ploy.aws.s3.list_buckets", return_value=["bucket1"]),
        ):
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="existing")),  # Bucket choice
                Mock(ask=Mock(return_value="manual")),  # Manual entry
                Mock(ask=Mock(return_value="public-read")),  # ACL
            ]

            mock_prompt.side_effect = [
                "my-manual-bucket",  # bucket_name
                ".",  # local_path
                "",  # bucket_path
            ]

            mock_confirm.side_effect = [False, True]  # cache, save_config

            result = prompts.prompt_for_bucket_config()

            assert result is not None
            assert result["bucket_name"] == "my-manual-bucket"

    def test_prompt_empty_bucket_name(self):
        """Test when user provides empty bucket name."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask", return_value=""),
        ):
            mock_select.return_value = Mock(ask=Mock(return_value="new"))

            result = prompts.prompt_for_bucket_config()

            assert result is None

    def test_prompt_with_recommended_cache(self):
        """Test prompting with recommended cache settings."""
        with (
            patch("questionary.select") as mock_select,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
            patch("rich.prompt.Confirm.ask") as mock_confirm,
        ):
            mock_select.side_effect = [
                Mock(ask=Mock(return_value="new")),
                Mock(ask=Mock(return_value="private")),
            ]
            mock_prompt.side_effect = ["bucket", ".", ""]
            mock_confirm.side_effect = [True, True]  # cache=True, save=True

            result = prompts.prompt_for_bucket_config()

            assert result is not None
            assert result.get("caches") == "recommended"


class TestConfirmDestructiveOperation:
    """Tests for confirm_destructive_operation function."""

    def test_confirm_destructive_operation_user_confirms(self):
        """Test when user confirms destructive operation."""
        with patch("rich.prompt.Confirm.ask", return_value=True):
            result = prompts.confirm_destructive_operation(
                operation="delete files",
                file_count=10,
            )

            assert result is True

    def test_confirm_destructive_operation_user_declines(self):
        """Test when user declines destructive operation."""
        with patch("rich.prompt.Confirm.ask", return_value=False):
            result = prompts.confirm_destructive_operation(
                operation="delete files",
                file_count=10,
            )

            assert result is False

    def test_confirm_destructive_operation_no_file_count(self):
        """Test when file_count is not provided."""
        with patch("rich.prompt.Confirm.ask", return_value=True):
            result = prompts.confirm_destructive_operation(operation="clear bucket")

            assert result is True


class TestPromptForACL:
    """Tests for prompt_for_acl function."""

    def test_prompt_for_acl_user_selects(self):
        """Test when user selects an ACL."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value = Mock(ask=Mock(return_value="private"))

            result = prompts.prompt_for_acl()

            assert result == "private"
            mock_select.assert_called_once()

    def test_prompt_for_acl_user_cancels(self):
        """Test when user cancels ACL selection."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value = Mock(ask=Mock(return_value=None))

            result = prompts.prompt_for_acl()

            # Should return default
            assert result == "public-read"

    def test_prompt_for_acl_returns_public_read_by_default(self):
        """Test that public-read is returned when user doesn't select."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value = Mock(ask=Mock(return_value=""))

            result = prompts.prompt_for_acl()

            assert result == "public-read"
