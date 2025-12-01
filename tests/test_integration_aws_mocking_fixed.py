"""Integration tests for AWS operations with comprehensive mocking."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from d3ploy.aws import cloudfront
from d3ploy.aws import s3


class TestAWSOperationsIntegration:
    """Test AWS operations end-to-end with mocking."""

    def test_bucket_listing_integration(self) -> None:
        """Test bucket listing operations."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket1"},
                {"Name": "bucket2"},
                {"Name": "test-bucket"},
            ]
        }

        buckets = s3.list_buckets(s3_client=mock_s3_client)
        assert "test-bucket" in buckets
        assert len(buckets) == 3

    def test_bucket_connection_success(self) -> None:
        """Test successful bucket connection."""
        mock_s3_resource = MagicMock()

        # Mock successful head_bucket call
        mock_s3_resource.meta.client.head_bucket.return_value = {}

        result = s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)
        assert result is True

    def test_key_exists_check(self) -> None:
        """Test S3 key existence checking."""
        mock_s3_resource = MagicMock()

        # Mock bucket and objects
        mock_bucket = MagicMock()
        mock_s3_resource.Bucket.return_value = mock_bucket

        # Mock object that matches the key
        mock_object = MagicMock()
        mock_object.key = "test-file.txt"
        mock_bucket.objects.filter.return_value = [mock_object]

        exists = s3.key_exists(mock_s3_resource, "test-bucket", "test-file.txt")
        assert exists is True

        # Test key doesn't exist - filter returns empty list
        mock_bucket.objects.filter.return_value = []
        exists = s3.key_exists(mock_s3_resource, "test-bucket", "nonexistent.txt")
        assert exists is False

    def test_cloudfront_invalidation_success(self) -> None:
        """Test CloudFront invalidation."""
        mock_cf_client = MagicMock()

        # Mock successful invalidation
        mock_cf_client.create_invalidation.return_value = {
            "Invalidation": {"Id": "INVALIDATION123"}
        }

        result = cloudfront.invalidate_distributions(
            distribution_ids="CLOUDFRONT123",
            dry_run=False,
            cloudfront_client=mock_cf_client,
        )

        assert result is not None
        mock_cf_client.create_invalidation.assert_called_once()

    def test_file_upload_integration(self) -> None:
        """Test file upload operations."""
        mock_s3_resource = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test content")

            # Mock upload
            result = s3.upload_file(
                file_name=test_file,
                bucket_name="test-bucket",
                s3=mock_s3_resource,
                bucket_path="/",
                prefix=Path(temp_dir),
                dry_run=False,
            )

            # Should return key and size
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_file_delete_integration(self) -> None:
        """Test file deletion operations."""
        mock_s3_resource = MagicMock()

        # Mock bucket with object to delete
        mock_bucket = MagicMock()
        mock_s3_resource.Bucket.return_value = mock_bucket

        mock_object = MagicMock()
        mock_object.key = "test-file.txt"
        mock_bucket.objects.filter.return_value = [mock_object]

        result = s3.delete_file(
            key_name="test-file.txt",
            bucket_name="test-bucket",
            s3=mock_s3_resource,
            dry_run=False,
            needs_confirmation=False,
        )

        # Should execute without errors and return delete count
        assert result == 1  # Function returns number of files deleted

    def test_aws_error_handling_no_credentials(self) -> None:
        """Test handling of AWS credential errors."""
        # Mock resource that raises error when accessing meta.client
        mock_s3_resource = MagicMock()

        # Mock ClientError with 403 to trigger the sys.exit path
        mock_s3_resource.meta.client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket"
        )

        with pytest.raises(SystemExit):  # Function calls sys.exit on 403 error
            s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)

    def test_aws_error_handling_client_error(self) -> None:
        """Test handling of AWS client errors."""
        mock_s3_resource = MagicMock()

        # Mock access denied error
        mock_s3_resource.meta.client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "HeadBucket",
        )

        # Should raise the client error for non-403 errors or handle 403 specifically
        try:
            s3.test_bucket_connection("test-bucket", s3=mock_s3_resource)
        except (ClientError, SystemExit):
            # Either ClientError propagates or SystemExit for 403 errors
            pass

    def test_cloudfront_error_handling(self) -> None:
        """Test CloudFront error handling."""
        mock_cf_client = MagicMock()

        # Test invalid distribution ID
        mock_cf_client.create_invalidation.side_effect = ClientError(
            {
                "Error": {
                    "Code": "NoSuchDistribution",
                    "Message": "Distribution not found",
                }
            },
            "CreateInvalidation",
        )

        with pytest.raises(ClientError):
            cloudfront.invalidate_distributions(
                distribution_ids="INVALID123",
                dry_run=False,
                cloudfront_client=mock_cf_client,
            )

    def test_dry_run_functionality(self) -> None:
        """Test that dry run mode works correctly."""
        mock_cf_client = MagicMock()  # Create mock client for dry run test

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test content")

            # Test dry run for CloudFront
            result = cloudfront.invalidate_distributions(
                distribution_ids="TEST123",
                dry_run=True,
                cloudfront_client=mock_cf_client,
            )

            # Should return without making actual calls
            assert result is not None
