"""
Signal handling for graceful shutdown.
"""

import os
import signal
import sys

from ..compat import colorama
from ..sync import operations


def bail(*args, **kwargs):
    """
    Handle shutdown signal.

    Args:
        *args: Signal arguments (signum, frame).
        **kwargs: Additional keyword arguments.
    """
    operations.killswitch.set()
    buffer = sys.stdout
    buffer.write(f"\n{colorama.Fore.RED}Exiting...{colorama.Style.RESET_ALL}\n")
    buffer.flush()
    sys.exit(os.EX_OK)


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
