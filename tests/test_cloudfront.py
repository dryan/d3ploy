"""
Tests for d3ploy.aws.cloudfront module.
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from d3ploy.aws import cloudfront


@pytest.fixture
def mock_cloudfront_client():
    """Mock boto3 CloudFront client."""
    with patch("d3ploy.aws.cloudfront.boto3.client") as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        yield client


def test_invalidate_distributions_single_id(mock_cloudfront_client):
    """Invalidate single distribution."""
    mock_cloudfront_client.create_invalidation.return_value = {
        "Invalidation": {"Id": "test-invalidation-id"}
    }

    result = cloudfront.invalidate_distributions("E123456")

    assert result == ["test-invalidation-id"]
    mock_cloudfront_client.create_invalidation.assert_called_once()
    call_args = mock_cloudfront_client.create_invalidation.call_args
    assert call_args[1]["DistributionId"] == "E123456"
    assert call_args[1]["InvalidationBatch"]["Paths"]["Items"] == ["/*"]


def test_invalidate_distributions_multiple_ids(mock_cloudfront_client):
    """Invalidate multiple distributions."""
    mock_cloudfront_client.create_invalidation.side_effect = [
        {"Invalidation": {"Id": "inv-1"}},
        {"Invalidation": {"Id": "inv-2"}},
    ]

    result = cloudfront.invalidate_distributions(["E123456", "E789012"])

    assert result == ["inv-1", "inv-2"]
    assert mock_cloudfront_client.create_invalidation.call_count == 2


def test_invalidate_distributions_list_with_single_id(mock_cloudfront_client):
    """Invalidate with list containing single ID."""
    mock_cloudfront_client.create_invalidation.return_value = {
        "Invalidation": {"Id": "test-id"}
    }

    result = cloudfront.invalidate_distributions(["E123456"])

    assert result == ["test-id"]
    assert mock_cloudfront_client.create_invalidation.call_count == 1


def test_invalidate_distributions_dry_run():
    """Dry run doesn't create invalidations."""
    result = cloudfront.invalidate_distributions("E123456", dry_run=True)

    assert result == []


def test_invalidate_distributions_dry_run_multiple():
    """Dry run with multiple IDs doesn't create invalidations."""
    result = cloudfront.invalidate_distributions(
        ["E123456", "E789012"],
        dry_run=True,
    )

    assert result == []


def test_invalidate_distributions_caller_reference(mock_cloudfront_client):
    """Each invalidation has unique CallerReference."""
    mock_cloudfront_client.create_invalidation.return_value = {
        "Invalidation": {"Id": "inv-1"}
    }

    # Call twice
    cloudfront.invalidate_distributions("E123456")
    cloudfront.invalidate_distributions("E123456")

    # Get CallerReference from both calls
    call1_ref = mock_cloudfront_client.create_invalidation.call_args_list[0][1][
        "InvalidationBatch"
    ]["CallerReference"]
    call2_ref = mock_cloudfront_client.create_invalidation.call_args_list[1][1][
        "InvalidationBatch"
    ]["CallerReference"]

    # Should be different (UUIDs)
    assert call1_ref != call2_ref


def test_invalidate_distributions_paths_all(mock_cloudfront_client):
    """Invalidates all paths (/*) to minimize cost."""
    mock_cloudfront_client.create_invalidation.return_value = {
        "Invalidation": {"Id": "test-id"}
    }

    cloudfront.invalidate_distributions("E123456")

    call_args = mock_cloudfront_client.create_invalidation.call_args
    paths = call_args[1]["InvalidationBatch"]["Paths"]
    assert paths["Quantity"] == 1
    assert paths["Items"] == ["/*"]


def test_invalidate_distributions_response_no_id(mock_cloudfront_client):
    """Handle response without invalidation ID."""
    mock_cloudfront_client.create_invalidation.return_value = {
        "Invalidation": {}  # Missing Id
    }

    result = cloudfront.invalidate_distributions("E123456")

    assert result == []


def test_invalidate_distributions_response_missing_invalidation_key(
    mock_cloudfront_client,
):
    """Handle response without Invalidation key."""
    mock_cloudfront_client.create_invalidation.return_value = {}

    result = cloudfront.invalidate_distributions("E123456")

    assert result == []


def test_invalidate_distributions_partial_success(mock_cloudfront_client):
    """Handle some successful, some failed invalidations."""
    mock_cloudfront_client.create_invalidation.side_effect = [
        {"Invalidation": {"Id": "inv-1"}},
        {"Invalidation": {}},  # Missing Id
        {"Invalidation": {"Id": "inv-3"}},
    ]

    result = cloudfront.invalidate_distributions(["E1", "E2", "E3"])

    assert result == ["inv-1", "inv-3"]


def test_invalidate_distributions_empty_list():
    """Handle empty distribution list."""
    result = cloudfront.invalidate_distributions([])

    assert result == []


def test_invalidate_distributions_client_error(mock_cloudfront_client):
    """Handle ClientError during invalidation."""
    from botocore.exceptions import ClientError

    mock_cloudfront_client.create_invalidation.side_effect = ClientError(
        {"Error": {"Code": "InvalidArgument", "Message": "Invalid distribution"}},
        "CreateInvalidation",
    )

    with pytest.raises(ClientError):
        cloudfront.invalidate_distributions("E123456")


def test_invalidate_distributions_no_credentials(mock_cloudfront_client):
    """Handle missing AWS credentials."""
    from botocore.exceptions import NoCredentialsError

    mock_cloudfront_client.create_invalidation.side_effect = NoCredentialsError()

    with pytest.raises(NoCredentialsError):
        cloudfront.invalidate_distributions("E123456")


def test_invalidate_distributions_access_denied(mock_cloudfront_client):
    """Handle access denied error."""
    from botocore.exceptions import ClientError

    mock_cloudfront_client.create_invalidation.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "CreateInvalidation",
    )

    with pytest.raises(ClientError):
        cloudfront.invalidate_distributions("E123456")


def test_invalidate_distributions_network_error(mock_cloudfront_client):
    """Handle network errors."""
    from botocore.exceptions import EndpointConnectionError

    mock_cloudfront_client.create_invalidation.side_effect = EndpointConnectionError(
        endpoint_url="https://cloudfront.amazonaws.com"
    )

    with pytest.raises(EndpointConnectionError):
        cloudfront.invalidate_distributions("E123456")
