"""
Tests for d3ploy.aws.s3 deletion functionality (DeleteFileTestCase conversion).
"""

import uuid
from unittest.mock import patch

import pytest

from d3ploy.aws import s3


@pytest.fixture
def uploaded_test_file(
    clean_s3_bucket, s3_resource, test_file_path, files_dir, test_bucket_name
):
    """Create and upload a test file to S3 for deletion tests."""
    # Create test file
    test_file_path.parent.mkdir(parents=True, exist_ok=True)
    test_file_path.write_text(f"{uuid.uuid4().hex}\n")

    # Upload to S3
    result = s3.upload_file(
        test_file_path,
        test_bucket_name,
        s3_resource,
        "test-delete",
        files_dir,
    )

    # Verify upload succeeded
    assert result[1] == 1, "Test file upload failed"
    assert s3.key_exists(
        s3_resource, test_bucket_name, result[0]
    ), "Test file not found in S3"

    key_name = result[0]
    yield key_name

    # Cleanup - delete if still exists
    if s3.key_exists(s3_resource, test_bucket_name, key_name):
        s3_resource.Object(test_bucket_name, key_name).delete()


# Tests for delete_file


def test_delete_file_dry_run(uploaded_test_file, s3_resource, test_bucket_name):
    """delete_file dry_run=True does not delete the file."""
    result = s3.delete_file(
        uploaded_test_file,
        test_bucket_name,
        s3_resource,
        dry_run=True,
    )

    assert result == 1, "dry_run should return 1"
    assert s3.key_exists(
        s3_resource, test_bucket_name, uploaded_test_file
    ), "File should still exist after dry_run"


def test_delete_file_deletion(uploaded_test_file, s3_resource, test_bucket_name):
    """delete_file successfully deletes the file."""
    result = s3.delete_file(
        uploaded_test_file,
        test_bucket_name,
        s3_resource,
    )

    assert result == 1, "Deletion should return 1"
    assert not s3.key_exists(
        s3_resource, test_bucket_name, uploaded_test_file
    ), "File should be deleted"


def test_delete_file_confirmation_affirmative(
    uploaded_test_file, s3_resource, test_bucket_name
):
    """delete_file with confirmation=True deletes when confirmed."""
    with patch("d3ploy.ui.dialogs.confirm_delete", return_value=True):
        result = s3.delete_file(
            uploaded_test_file,
            test_bucket_name,
            s3_resource,
            needs_confirmation=True,
        )

        assert result == 1, "Should return 1 when confirmed"
        assert not s3.key_exists(
            s3_resource, test_bucket_name, uploaded_test_file
        ), "File should be deleted when confirmed"


def test_delete_file_confirmation_negative(
    uploaded_test_file, s3_resource, test_bucket_name
):
    """delete_file with confirmation=True skips deletion when not confirmed."""
    with patch("d3ploy.ui.dialogs.confirm_delete", return_value=False):
        result = s3.delete_file(
            uploaded_test_file,
            test_bucket_name,
            s3_resource,
            needs_confirmation=True,
        )

        assert result == 0, "Should return 0 when not confirmed"
        assert s3.key_exists(
            s3_resource, test_bucket_name, uploaded_test_file
        ), "File should not be deleted when not confirmed"


def test_delete_file_with_killswitch_flipped(
    uploaded_test_file, s3_resource, test_bucket_name
):
    """delete_file raises UserCancelled when signal received during operation."""
    from unittest.mock import MagicMock

    from d3ploy.core.signals import UserCancelled
    from d3ploy.sync import operations

    # Simulate signal being triggered during deletion
    def raise_cancelled(*args, **kwargs):
        operations.killswitch.set()
        raise UserCancelled("Operation cancelled")

    # Mock the Object().delete() call to raise UserCancelled
    mock_obj = MagicMock()
    mock_obj.delete.side_effect = raise_cancelled

    with (
        patch.object(s3_resource, "Object", return_value=mock_obj),
        pytest.raises(UserCancelled),
    ):
        s3.delete_file(
            uploaded_test_file,
            test_bucket_name,
            s3_resource,
        )
