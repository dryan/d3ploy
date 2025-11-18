"""
Main application wrapper for UI operations.
"""

from typing import Any
from typing import Callable

from rich.console import Console


class D3ployApp:
    """
    Application wrapper for d3ploy operations with UI support.

    This class provides a context for running d3ploy operations
    with or without UI enhancements.
    """

    def __init__(self, *, quiet: bool = False):
        """
        Initialize the application.

        Args:
            quiet: If True, suppress all non-error output.
        """
        self.quiet = quiet
        self.console = Console()

    def run_sync(
        self,
        sync_func: Callable,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Execute sync operation with UI context.

        Args:
            sync_func: The sync function to execute.
            *args: Positional arguments for sync function.
            **kwargs: Keyword arguments for sync function.

        Returns:
            Result from sync_func.
        """
        # Pass quiet flag to sync function
        kwargs.setdefault("quiet", self.quiet)

        # Execute the sync function
        return sync_func(*args, **kwargs)
