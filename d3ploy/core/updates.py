"""
Version checking and update notifications.
"""

from typing import Optional


def check_for_updates(current_version: str) -> Optional[str]:
    """
    Check PyPI for newer version.

    Args:
        current_version: Current version string.

    Returns:
        New version string if available, None otherwise.
    """
    # TODO: Implement in Phase 3.5
    raise NotImplementedError("Update checking will be implemented in Phase 3.5")


def display_update_notification(new_version: str):
    """
    Display update available notification.

    Args:
        new_version: Version string of available update.
    """
    # TODO: Implement in Phase 3.5
    raise NotImplementedError("Update notification will be implemented in Phase 3.5")


def get_last_check_time() -> int:
    """
    Get timestamp of last update check.

    Returns:
        Unix timestamp of last check, or 0 if never checked.
    """
    # TODO: Implement in Phase 3.5
    raise NotImplementedError("Check time tracking will be implemented in Phase 3.5")


def save_check_time(timestamp: int):
    """
    Save timestamp of update check.

    Args:
        timestamp: Unix timestamp to save.
    """
    # TODO: Implement in Phase 3.5
    raise NotImplementedError("Check time saving will be implemented in Phase 3.5")
