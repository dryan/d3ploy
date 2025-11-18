"""
Core application logic for d3ploy.

This module contains the main CLI entry point, update checking,
and signal handling.
"""

from .cli import cli
from .signals import setup_signal_handlers
from .updates import check_for_updates

__all__ = ["cli", "check_for_updates", "setup_signal_handlers"]
