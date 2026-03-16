"""
Tests for d3ploy.sync.operations module.
"""

import os
import threading
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from d3ploy.sync import operations


@pytest.fixture
def reset_killswitch():
    """Reset killswitch before and after each test."""
    operations.killswitch.clear()
    yield
    operations.killswitch.clear()


# Tests for get_progress_bar


def test_get_progress_bar_with_args():
    """Create progress bar with positional args."""
    # When called with positional args, description must be passed as kwarg
    progress = operations.get_progress_bar(100, description="Uploading")

    assert progress.total == 100
    assert progress.description == "Uploading"
    assert not progress.disable


def test_get_progress_bar_with_kwargs():
    """Create progress bar with keyword args."""
    progress = operations.get_progress_bar(
        total=50,
        description="Processing",
    )

    assert progress.total == 50
    assert progress.description == "Processing"


def test_get_progress_bar_quiet_mode():
    """Create disabled progress bar in quiet mode."""
    progress = operations.get_progress_bar(100, "Test", quiet=True)

    assert progress.disable is True


def test_get_progress_bar_custom_unit():
    """Create progress bar with custom unit."""
    progress = operations.get_progress_bar(100, desc="Test", unit="bytes")

    # Unit is passed to Rich but not stored as attribute
    assert progress.total == 100


def test_get_progress_bar_custom_colour():
    """Create progress bar with custom colour."""
    progress = operations.get_progress_bar(100, desc="Test", colour="blue")

    # Colour is passed to Rich but not stored as attribute
    assert progress.total == 100


# Tests for alert


def test_alert_info_message():
    """Display info message without exiting."""
    with patch("d3ploy.sync.operations.ui.output.display_message") as mock_display:
        operations.alert("Test message")

        mock_display.assert_called_once_with(
            "Test message",
            level="info",
            quiet=False,
        )


def test_alert_error_message_with_exit():
    """Display error and exit with error code."""
    with patch("d3ploy.sync.operations.ui.output.display_message") as mock_display:
        with pytest.raises(SystemExit) as exc_info:
            operations.alert("Error message", error_code=1)

        assert exc_info.value.code == 1
        mock_display.assert_called_once()
        assert mock_display.call_args[1]["level"] == "error"


def test_alert_success_message():
    """Display success message with EX_OK."""
    with patch("d3ploy.sync.operations.ui.output.display_message") as mock_display:
        with pytest.raises(SystemExit) as exc_info:
            operations.alert("Success", error_code=os.EX_OK)

        assert exc_info.value.code == os.EX_OK
        mock_display.assert_called_once()
        assert mock_display.call_args[1]["level"] == "success"


def test_alert_quiet_mode():
    """Alert respects quiet mode."""
    with patch("d3ploy.sync.operations.ui.output.display_message") as mock_display:
        operations.alert("Test", quiet=True)

        mock_display.assert_called_once()
        assert mock_display.call_args[1]["quiet"] is True


def test_alert_no_exit_without_error_code():
    """Alert doesn't exit when error_code is None."""
    with patch("d3ploy.sync.operations.ui.output.display_message"):
        # Should not raise SystemExit
        operations.alert("Test message")


# Tests for get_confirmation


def test_get_confirmation_yes(monkeypatch):
    """Return True when user confirms with 'y'."""
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = operations.get_confirmation("Proceed?")

    assert result is True


def test_get_confirmation_yes_full(monkeypatch):
    """Return True when user confirms with 'yes'."""
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    result = operations.get_confirmation("Proceed?")

    assert result is True


def test_get_confirmation_no(monkeypatch):
    """Return False when user declines with 'n'."""
    monkeypatch.setattr("builtins.input", lambda _: "n")

    result = operations.get_confirmation("Proceed?")

    assert result is False


def test_get_confirmation_empty(monkeypatch):
    """Return False for empty input."""
    monkeypatch.setattr("builtins.input", lambda _: "")

    result = operations.get_confirmation("Proceed?")

    assert result is False


def test_get_confirmation_case_insensitive(monkeypatch):
    """Confirmation is case insensitive."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    assert operations.get_confirmation("Proceed?") is True

    monkeypatch.setattr("builtins.input", lambda _: "YES")
    assert operations.get_confirmation("Proceed?") is True

    monkeypatch.setattr("builtins.input", lambda _: "Yes")
    assert operations.get_confirmation("Proceed?") is True


def test_get_confirmation_invalid_input(monkeypatch):
    """Return False for invalid input."""
    monkeypatch.setattr("builtins.input", lambda _: "maybe")

    result = operations.get_confirmation("Proceed?")

    assert result is False


# Tests for killswitch


def test_killswitch_initially_clear(reset_killswitch):
    """Killswitch is initially cleared."""
    assert not operations.killswitch.is_set()


def test_killswitch_can_be_set(reset_killswitch):
    """Killswitch can be set."""
    operations.killswitch.set()

    assert operations.killswitch.is_set()


def test_killswitch_can_be_cleared(reset_killswitch):
    """Killswitch can be cleared."""
    operations.killswitch.set()
    operations.killswitch.clear()

    assert not operations.killswitch.is_set()


def test_killswitch_thread_safe(reset_killswitch):
    """Killswitch is thread-safe."""
    results = []

    def check_killswitch():
        results.append(operations.killswitch.is_set())

    operations.killswitch.set()

    threads = [threading.Thread(target=check_killswitch) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(results)
    assert len(results) == 10


# Tests for upload_batch


def test_upload_batch_empty_list(reset_killswitch):
    """Handle empty file list."""
    mock_s3 = MagicMock()

    results, total = operations.upload_batch(
        [],
        "test-bucket",
        mock_s3,
        "prefix",
        Path("/local"),
    )

    assert results == []
    assert total == 0


def test_upload_batch_single_file(tmp_path, reset_killswitch):
    """Upload single file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_s3 = MagicMock()

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.return_value = ("prefix/test.txt", 1)

        results, total = operations.upload_batch(
            [test_file],
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
        )

    assert len(results) == 1
    assert results[0] == ("prefix/test.txt", 1)
    assert total == 1


def test_upload_batch_multiple_files(tmp_path, reset_killswitch):
    """Upload multiple files."""
    files = []
    for i in range(3):
        f = tmp_path / f"file{i}.txt"
        f.write_text(f"content{i}")
        files.append(f)

    mock_s3 = MagicMock()

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.side_effect = [(f"prefix/file{i}.txt", 1) for i in range(3)]

        results, total = operations.upload_batch(
            files,
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
            processes=2,
        )

    assert len(results) == 3
    assert total == 3


def test_upload_batch_dry_run(tmp_path, reset_killswitch):
    """Dry run doesn't upload files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_s3 = MagicMock()

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.return_value = ("prefix/test.txt", 1)

        results, total = operations.upload_batch(
            [test_file],
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
            dry_run=True,
        )

    # Should still call upload_file (it handles dry_run internally)
    mock_upload.assert_called_once()
    assert mock_upload.call_args[1]["dry_run"] is True


def test_upload_batch_with_acl(tmp_path, reset_killswitch):
    """Pass ACL to upload_file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_s3 = MagicMock()

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.return_value = ("prefix/test.txt", 1)

        operations.upload_batch(
            [test_file],
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
            acl="public-read",
        )

    assert mock_upload.call_args[1]["acl"] == "public-read"


def test_upload_batch_with_caches(tmp_path, reset_killswitch):
    """Pass caches to upload_file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    mock_s3 = MagicMock()
    caches = {"text/plain": 3600}

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.return_value = ("prefix/test.txt", 1)

        operations.upload_batch(
            [test_file],
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
            caches=caches,
        )

    assert mock_upload.call_args[1]["caches"] == caches


def test_upload_batch_respects_killswitch(tmp_path, reset_killswitch):
    """Stop uploading when killswitch is set."""
    files = [tmp_path / f"file{i}.txt" for i in range(10)]
    for f in files:
        f.write_text("content")

    mock_s3 = MagicMock()
    upload_count = 0

    def upload_and_kill(*args, **kwargs):
        nonlocal upload_count
        upload_count += 1
        if upload_count == 2:  # Set killswitch after second upload
            operations.killswitch.set()
        return ("test", 1)

    with patch("d3ploy.sync.operations.aws.s3.upload_file") as mock_upload:
        mock_upload.side_effect = upload_and_kill

        # Killswitch will stop processing remaining files
        results, total = operations.upload_batch(
            files,
            "test-bucket",
            mock_s3,
            "prefix",
            tmp_path,
        )

    # Should stop early when killswitch is set
    assert len(results) < len(files)
    assert upload_count >= 2


# Tests for delete_orphans


def test_delete_orphans_empty_bucket(reset_killswitch):
    """Handle bucket with no orphaned files."""
    mock_s3 = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.objects.filter.return_value = []
    mock_s3.Bucket.return_value = mock_bucket

    deleted = operations.delete_orphans(
        "test-bucket",
        mock_s3,
        "/prefix",
        ["file1.txt", "file2.txt"],
    )

    assert deleted == 0


def test_delete_orphans_with_orphans(reset_killswitch):
    """Delete files that don't exist locally."""
    mock_s3 = MagicMock()
    mock_bucket = MagicMock()

    # Create mock S3 objects
    mock_key1 = MagicMock()
    mock_key1.key = "prefix/orphan1.txt"
    mock_key2 = MagicMock()
    mock_key2.key = "prefix/orphan2.txt"

    mock_bucket.objects.filter.return_value = [mock_key1, mock_key2]
    mock_s3.Bucket.return_value = mock_bucket

    with patch("d3ploy.sync.operations.aws.s3.delete_file") as mock_delete:
        mock_delete.return_value = 1

        deleted = operations.delete_orphans(
            "test-bucket",
            mock_s3,
            "/prefix",
            ["prefix/keep.txt"],  # Local files to keep
            processes=2,
        )

    assert deleted == 2
    assert mock_delete.call_count == 2


def test_delete_orphans_dry_run(reset_killswitch):
    """Dry run doesn't delete files."""
    mock_s3 = MagicMock()
    mock_bucket = MagicMock()

    mock_key = MagicMock()
    mock_key.key = "prefix/orphan.txt"

    mock_bucket.objects.filter.return_value = [mock_key]
    mock_s3.Bucket.return_value = mock_bucket

    with patch("d3ploy.sync.operations.aws.s3.delete_file") as mock_delete:
        mock_delete.return_value = 1

        operations.delete_orphans(
            "test-bucket",
            mock_s3,
            "/prefix",
            [],
            dry_run=True,
        )

    # Should still call delete_file (it handles dry_run internally)
    assert mock_delete.call_args[1]["dry_run"] is True


def test_delete_orphans_with_confirmation(reset_killswitch, monkeypatch):
    """Prompt for confirmation before each deletion."""
    mock_s3 = MagicMock()
    mock_bucket = MagicMock()

    mock_key = MagicMock()
    mock_key.key = "prefix/orphan.txt"

    mock_bucket.objects.filter.return_value = [mock_key]
    mock_s3.Bucket.return_value = mock_bucket

    # Decline confirmation
    monkeypatch.setattr("builtins.input", lambda _: "n")

    with (
        patch("d3ploy.sync.operations.aws.s3.delete_file") as mock_delete,
        patch("d3ploy.sync.operations.alert") as mock_alert,
    ):
        operations.delete_orphans(
            "test-bucket",
            mock_s3,
            "/prefix",
            [],
            needs_confirmation=True,
        )

    # Should not delete when declined
    mock_delete.assert_not_called()
    # Should show skip message
    mock_alert.assert_called()
    assert "Skipping" in mock_alert.call_args[0][0]


def test_delete_orphans_respects_killswitch(reset_killswitch):
    """Stop deleting when killswitch is set."""
    mock_s3 = MagicMock()
    mock_bucket = MagicMock()

    # Create multiple orphans
    orphans = [MagicMock() for _ in range(5)]
    for i, orphan in enumerate(orphans):
        orphan.key = f"prefix/orphan{i}.txt"

    mock_bucket.objects.filter.return_value = orphans
    mock_s3.Bucket.return_value = mock_bucket

    delete_count = 0

    def delete_and_kill(*args, **kwargs):
        nonlocal delete_count
        delete_count += 1
        if delete_count == 2:
            operations.killswitch.set()
        return 1

    with patch("d3ploy.sync.operations.aws.s3.delete_file") as mock_delete:
        mock_delete.side_effect = delete_and_kill

        deleted = operations.delete_orphans(
            "test-bucket",
            mock_s3,
            "/prefix",
            [],
        )

    # Should stop early
    assert deleted < len(orphans)


# Tests for sync_target


def test_sync_target_missing_bucket(tmp_path, reset_killswitch):
    """Exit with error when bucket is not specified."""
    with pytest.raises(SystemExit) as exc_info:
        operations.sync_target(
            "test-target",
            bucket_name=None,
            local_path=tmp_path,
        )

    assert exc_info.value.code == os.EX_NOINPUT


def test_sync_target_basic_sync(tmp_path, reset_killswitch):
    """Perform basic sync operation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch("d3ploy.sync.operations.ui.output.display_message"),
    ):
        mock_discover.return_value = [test_file]
        mock_upload.return_value = ([("prefix/test.txt", 1)], 1)

        result = operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            bucket_path="/prefix",
        )

    assert result["uploaded"] == 1
    assert result["deleted"] == 0
    assert result["invalidated"] == 0


def test_sync_target_with_delete(tmp_path, reset_killswitch):
    """Sync and delete orphaned files."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch("d3ploy.sync.operations.delete_orphans") as mock_delete,
        patch("d3ploy.sync.operations.ui.output.display_message"),
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([], 0)
        mock_delete.return_value = 3

        result = operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            delete=True,
        )

    assert result["deleted"] == 3
    mock_delete.assert_called_once()


def test_sync_target_with_cloudfront(tmp_path, reset_killswitch):
    """Sync and invalidate CloudFront."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch(
            "d3ploy.sync.operations.aws.cloudfront.invalidate_distributions"
        ) as mock_invalidate,
        patch("d3ploy.sync.operations.ui.output.display_message"),
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([("test.txt", 1)], 1)
        mock_invalidate.return_value = ["ABC123"]

        result = operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            cloudfront_id="ABC123",
        )

    assert result["invalidated"] == 1
    mock_invalidate.assert_called_once_with("ABC123", dry_run=False)


def test_sync_target_cloudfront_skip_no_changes(tmp_path, reset_killswitch):
    """Skip CloudFront invalidation when no files changed."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch(
            "d3ploy.sync.operations.aws.cloudfront.invalidate_distributions"
        ) as mock_invalidate,
        patch("d3ploy.sync.operations.alert"),
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([], 0)

        result = operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            cloudfront_id="ABC123",
        )

    assert result["invalidated"] == 0
    mock_invalidate.assert_not_called()


def test_sync_target_dry_run(tmp_path, reset_killswitch):
    """Dry run sync operation."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch("d3ploy.sync.operations.ui.output.display_message") as mock_display,
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([], 2)

        operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            dry_run=True,
        )

    # Check dry run was passed to upload_batch
    assert mock_upload.call_args[1]["dry_run"] is True
    # Check message mentions "would be"
    assert any("would be" in str(call[0][0]) for call in mock_display.call_args_list)


def test_sync_target_cloudfront_dry_run(tmp_path, reset_killswitch):
    """Dry run with CloudFront invalidation shows 'would be requested' message."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch("d3ploy.sync.operations.ui.output.display_message") as mock_display,
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([("test.txt", 1)], 1)

        operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            cloudfront_id="ABC123",
            dry_run=True,
        )

    # Check message mentions CloudFront invalidation "would be requested"
    assert any(
        "would be requested" in str(call[0][0]) for call in mock_display.call_args_list
    )


def test_sync_target_cloudfront_id_none(tmp_path, reset_killswitch):
    """Test sync_target with cloudfront_id=None and using_config=False (line 308)."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.discovery.discover_files") as mock_discover,
        patch("d3ploy.sync.operations.upload_batch") as mock_upload,
        patch("d3ploy.sync.operations.alert") as mock_alert,
    ):
        mock_discover.return_value = []
        mock_upload.return_value = ([], 0)

        result = operations.sync_target(
            "test-target",
            bucket_name="test-bucket",
            local_path=tmp_path,
            cloudfront_id=None,
            using_config=False,
        )

    # Should not have invalidated anything
    assert result["invalidated"] == 0
    # Should have called alert with "Syncing to..." message (not using config)
    alert_calls = [str(call[0][0]) for call in mock_alert.call_args_list]
    assert any("Syncing to" in call for call in alert_calls)


def test_sync_target_local_path_none(tmp_path, reset_killswitch):
    """Test sync_target with local_path=None raises error."""
    with (
        patch("d3ploy.sync.operations.aws.s3.get_s3_resource"),
        patch("d3ploy.sync.operations.aws.s3.test_bucket_connection"),
        patch("d3ploy.sync.operations.alert") as mock_alert,
    ):
        # Let first alert pass, but second one (local_path=None) should exit
        def alert_side_effect(*args, **kwargs):
            # Check if this is the local_path error (has error_code)
            if "error_code" in kwargs:
                raise SystemExit(kwargs["error_code"])

        mock_alert.side_effect = alert_side_effect

        with pytest.raises(SystemExit) as exc_info:
            operations.sync_target(
                "test-target",
                bucket_name="test-bucket",
                local_path=None,
            )

        assert exc_info.value.code == os.EX_NOINPUT
        # Should have alerted about missing local path
        alert_calls = [str(call[0][0]) for call in mock_alert.call_args_list]
        assert any("local path was not specified" in call for call in alert_calls)
