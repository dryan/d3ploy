"""
CloudFront operations.
"""

import uuid
from typing import List
from typing import Union

import boto3


def invalidate_distributions(
    distribution_ids: Union[List[str], str],
    *,
    dry_run: bool = False,
    cloudfront_client=None,
) -> List[str]:
    """
    Create CloudFront cache invalidations.

    Args:
        distribution_ids: CloudFront distribution ID or list of IDs.
        dry_run: Simulate invalidation without actually creating.
        cloudfront_client: Optional CloudFront client. If None, creates a new one.

    Returns:
        List of invalidation IDs created.
    """
    output = []

    if not isinstance(distribution_ids, list):
        distribution_ids = [distribution_ids]

    for cf_id in distribution_ids:
        if not dry_run:
            if cloudfront_client is None:
                cloudfront_client = boto3.client("cloudfront")
            # we don't specify the individual paths because that's more
            # costly monetarily speaking
            response = cloudfront_client.create_invalidation(
                DistributionId=cf_id,
                InvalidationBatch={
                    "Paths": {"Quantity": 1, "Items": ["/*"]},
                    "CallerReference": uuid.uuid4().hex,
                },
            )
            invalidation_id = response.get("Invalidation", {}).get("Id")
            if invalidation_id:
                output.append(invalidation_id)

    return output
