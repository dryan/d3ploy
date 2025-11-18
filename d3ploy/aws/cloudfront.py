"""
CloudFront operations.
"""

from typing import List


def invalidate_distributions(
    distribution_ids: List[str],
    paths: List[str],
    dry_run: bool = False,
) -> List[str]:
    """
    Create CloudFront cache invalidations.

    Args:
        distribution_ids: List of CloudFront distribution IDs.
        paths: List of paths to invalidate.
        dry_run: Simulate invalidation without actually creating.

    Returns:
        List of invalidation IDs created.
    """
    # TODO: Implement in Phase 3.2
    raise NotImplementedError(
        "CloudFront invalidation will be implemented in Phase 3.2"
    )
