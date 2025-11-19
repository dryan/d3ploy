"""
Additional tests for d3ploy.aws.s3 module (beyond existing upload/delete tests).
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import botocore.exceptions
import pytest

from d3ploy.aws import s3


@pytest.fixture
def mock_s3_resource():
    """Mock S3 resource."""
    mock_resource = MagicMock()
    return mock_resource


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    mock_client = MagicMock()
    return mock_client


# Tests for get_s3_resource


def test_get_s3_resource():
    """get_s3_resource returns boto3 resource."""
    with patch("d3ploy.aws.s3.boto3.resource") as mock_resource:
        result = s3.get_s3_resource()

        mock_resource.assert_called_once_with("s3")
        assert result == mock_resource.return_value


# Tests for list_buckets


def test_list_buckets_success():
    """list_buckets returns list of bucket names."""
    with patch("d3ploy.aws.s3.boto3.client") as mock_client:
        client = MagicMock()
        client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket1"},
                {"Name": "bucket2"},
                {"Name": "bucket3"},
            ]
        }
        mock_client.return_value = client

        result = s3.list_buckets()

        assert result == ["bucket1", "bucket2", "bucket3"]


def test_list_buckets_empty():
    """list_buckets returns empty list when no buckets."""
    with patch("d3ploy.aws.s3.boto3.client") as mock_client:
        client = MagicMock()
        client.list_buckets.return_value = {"Buckets": []}
        mock_client.return_value = client

        result = s3.list_buckets()

        assert result == []


def test_list_buckets_missing_buckets_key():
    """list_buckets handles missing Buckets key."""
    with patch("d3ploy.aws.s3.boto3.client") as mock_client:
        client = MagicMock()
        client.list_buckets.return_value = {}
        mock_client.return_value = client

        result = s3.list_buckets()

        assert result == []


def test_list_buckets_client_error():
    """list_buckets returns empty list on ClientError."""
    with patch("d3ploy.aws.s3.boto3.client") as mock_client:
        client = MagicMock()
        client.list_buckets.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "ListBuckets",
        )
        mock_client.return_value = client

        result = s3.list_buckets()

        assert result == []


def test_list_buckets_no_credentials():
    """list_buckets raises NoCredentialsError when no credentials."""
    with patch("d3ploy.aws.s3.boto3.client") as mock_client:
        client = MagicMock()
        client.list_buckets.side_effect = botocore.exceptions.NoCredentialsError()
        mock_client.return_value = client

        with pytest.raises(botocore.exceptions.NoCredentialsError):
            s3.list_buckets()


# Tests for test_bucket_connection


def test_test_bucket_connection_success(mock_s3_resource):
    """test_bucket_connection returns True when successful."""
    mock_s3_resource.meta.client.head_bucket.return_value = {}

    result = s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)

    assert result is True
    mock_s3_resource.meta.client.head_bucket.assert_called_once_with(
        Bucket="test-bucket"
    )


def test_test_bucket_connection_creates_resource_if_none():
    """test_bucket_connection creates resource if not provided."""
    with patch("d3ploy.aws.s3.get_s3_resource") as mock_get_resource:
        mock_resource = MagicMock()
        mock_resource.meta.client.head_bucket.return_value = {}
        mock_get_resource.return_value = mock_resource

        result = s3.test_bucket_connection("test-bucket")

        assert result is True
        mock_get_resource.assert_called_once()


def test_test_bucket_connection_access_denied(mock_s3_resource, capsys):
    """test_bucket_connection exits on 403 error."""
    mock_s3_resource.meta.client.head_bucket.side_effect = (
        botocore.exceptions.ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}},
            "HeadBucket",
        )
    )

    with patch("d3ploy.aws.s3.boto3.Session") as mock_session:
        mock_credentials = MagicMock()
        mock_credentials.access_key = "AKIAIOSFODNN7EXAMPLE"
        mock_session.return_value.get_credentials.return_value = mock_credentials

        with pytest.raises(SystemExit) as exc_info:
            s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)

        assert exc_info.value.code == 67  # os.EX_NOUSER
        captured = capsys.readouterr()
        assert "test-bucket" in captured.err
        assert "AKIAIOSFODNN7EXAMPLE" in captured.err


def test_test_bucket_connection_access_denied_no_credentials(
    mock_s3_resource,
    capsys,
):
    """test_bucket_connection handles missing credentials."""
    mock_s3_resource.meta.client.head_bucket.side_effect = (
        botocore.exceptions.ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}},
            "HeadBucket",
        )
    )

    with patch("d3ploy.aws.s3.boto3.Session") as mock_session:
        mock_session.return_value.get_credentials.return_value = None

        with pytest.raises(SystemExit):
            s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)

        captured = capsys.readouterr()
        assert "unknown" in captured.err


def test_test_bucket_connection_other_error(mock_s3_resource):
    """test_bucket_connection raises other ClientErrors."""
    error = botocore.exceptions.ClientError(
        {"Error": {"Code": "500", "Message": "Server error"}},
        "HeadBucket",
    )
    mock_s3_resource.meta.client.head_bucket.side_effect = error

    with pytest.raises(botocore.exceptions.ClientError) as exc_info:
        s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)

    assert exc_info.value == error


# Tests for key_exists


def test_key_exists_true(mock_s3_resource):
    """key_exists returns True when key exists."""
    mock_bucket = MagicMock()
    mock_obj = MagicMock()
    mock_obj.key = "path/to/file.txt"
    mock_bucket.objects.filter.return_value = [mock_obj]
    mock_s3_resource.Bucket.return_value = mock_bucket

    result = s3.key_exists(mock_s3_resource, "test-bucket", "path/to/file.txt")

    assert result is True
    mock_s3_resource.Bucket.assert_called_once_with("test-bucket")
    mock_bucket.objects.filter.assert_called_once_with(Prefix="path/to/file.txt")


def test_key_exists_false(mock_s3_resource):
    """key_exists returns False when key doesn't exist."""
    mock_bucket = MagicMock()
    mock_bucket.objects.filter.return_value = []
    mock_s3_resource.Bucket.return_value = mock_bucket

    result = s3.key_exists(mock_s3_resource, "test-bucket", "nonexistent.txt")

    assert result is False


def test_key_exists_prefix_match_but_not_exact(mock_s3_resource):
    """key_exists returns False when prefix matches but not exact key."""
    mock_bucket = MagicMock()
    mock_obj1 = MagicMock()
    mock_obj1.key = "file.txt.backup"
    mock_obj2 = MagicMock()
    mock_obj2.key = "file.txt.old"
    mock_bucket.objects.filter.return_value = [mock_obj1, mock_obj2]
    mock_s3_resource.Bucket.return_value = mock_bucket

    result = s3.key_exists(mock_s3_resource, "test-bucket", "file.txt")

    assert result is False


def test_key_exists_multiple_objects_with_match(mock_s3_resource):
    """key_exists returns True when exact match exists among multiple."""
    mock_bucket = MagicMock()
    mock_obj1 = MagicMock()
    mock_obj1.key = "path/file.txt.old"
    mock_obj2 = MagicMock()
    mock_obj2.key = "path/file.txt"  # Exact match
    mock_obj3 = MagicMock()
    mock_obj3.key = "path/file.txt.backup"
    mock_bucket.objects.filter.return_value = [mock_obj1, mock_obj2, mock_obj3]
    mock_s3_resource.Bucket.return_value = mock_bucket

    result = s3.key_exists(mock_s3_resource, "test-bucket", "path/file.txt")

    assert result is True


# Tests for delete_file


def test_delete_file_success(mock_s3_resource):
    """delete_file successfully deletes object."""
    mock_obj = MagicMock()
    mock_s3_resource.Object.return_value = mock_obj

    result = s3.delete_file("path/to/file.txt", "test-bucket", mock_s3_resource)

    assert result == 1
    mock_s3_resource.Object.assert_called_once_with("test-bucket", "path/to/file.txt")
    mock_obj.delete.assert_called_once()


def test_delete_file_dry_run(mock_s3_resource):
    """delete_file dry_run doesn't delete."""
    result = s3.delete_file(
        "path/to/file.txt",
        "test-bucket",
        mock_s3_resource,
        dry_run=True,
    )

    assert result == 1
    # Should not call Object or delete
    mock_s3_resource.Object.assert_not_called()


def test_delete_file_needs_confirmation_yes():
    """delete_file with confirmation deletes when confirmed."""
    from d3ploy.ui import dialogs

    mock_s3 = MagicMock()

    with patch.object(dialogs, "confirm_delete", return_value=True):
        result = s3.delete_file(
            "path/to/file.txt",
            "test-bucket",
            mock_s3,
            needs_confirmation=True,
        )

    assert result == 1
    mock_s3.Object.return_value.delete.assert_called_once()


def test_delete_file_needs_confirmation_no():
    """delete_file with confirmation skips when not confirmed."""
    from d3ploy.ui import dialogs

    mock_s3 = MagicMock()

    with patch.object(dialogs, "confirm_delete", return_value=False):
        result = s3.delete_file(
            "path/to/file.txt",
            "test-bucket",
            mock_s3,
            needs_confirmation=True,
        )

    assert result == 0
    mock_s3.Object.return_value.delete.assert_not_called()


def test_delete_file_client_error(mock_s3_resource):
    """delete_file handles ClientError."""
    mock_obj = MagicMock()
    mock_obj.delete.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
        "DeleteObject",
    )
    mock_s3_resource.Object.return_value = mock_obj

    with pytest.raises(botocore.exceptions.ClientError):
        s3.delete_file("path/to/file.txt", "test-bucket", mock_s3_resource)
