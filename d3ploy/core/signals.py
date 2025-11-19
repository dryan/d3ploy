"""
Signal handling for graceful shutdown.
"""

import signal

from ..sync import operations


class UserCancelled(Exception):
    """Exception raised when user cancels operation (Ctrl+C)."""

    pass


def bail(*args, **kwargs):
    """
    Handle shutdown signal.

    Args:
        *args: Signal arguments (signum, frame).
        **kwargs: Additional keyword arguments.

    Raises:
        UserCancelled: Always raised to trigger clean exit.
    """
    operations.killswitch.set()
    raise UserCancelled("Operation cancelled by user")


def setup_signal_handlers():
    """
    Register signal handlers for SIGINT and SIGTERM.

    Enables graceful shutdown when receiving interrupt signals.
    """
    signal.signal(signal.SIGINT, bail)


def shutdown_requested() -> bool:
    """
    Check if shutdown has been requested.

    Returns:
        True if shutdown signal received.
    """
    return operations.killswitch.is_set()
