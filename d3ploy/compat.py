#!/usr/bin/env python3
"""
Temporary compatibility layer for colorama and tqdm functionality.
This module provides minimal replacements to keep the app functional
during the transition to Textual.

This file will be removed in Phase 3 when we implement the Textual UI.
"""

import sys
import time


# Colorama compatibility
class _MockFore:
    RED = ""
    GREEN = ""
    YELLOW = ""


class _MockStyle:
    RESET_ALL = ""


class _MockColorama:
    Fore = _MockFore()
    Style = _MockStyle()


def colorama_init():
    """Mock colorama initialization"""
    pass


# tqdm compatibility
class MockTqdm:
    """Minimal tqdm replacement for progress bars"""

    def __init__(self, *args, **kwargs):
        self.desc = kwargs.get("desc", "")
        self.total = kwargs.get("total", None)
        self.disable = kwargs.get("disable", False)
        self.current = 0
        self._last_print = 0

    def update(self, n=1):
        """Update progress by n steps"""
        self.current += n
        self._maybe_print()

    def set_description(self, desc):
        """Set description text"""
        self.desc = desc
        self._maybe_print()

    def _maybe_print(self):
        """Print progress occasionally to avoid spam"""
        now = time.time()
        if now - self._last_print > 0.5:  # Print every 0.5 seconds max
            if self.total:
                percent = (self.current / self.total) * 100
                print(
                    f"\r{self.desc} {self.current}/{self.total} ({percent:.1f}%)",
                    end="",
                    file=sys.stderr,
                )
            else:
                print(f"\r{self.desc} {self.current}", end="", file=sys.stderr)
            self._last_print = now

    def close(self):
        """Close progress bar"""
        if not self.disable:
            print("", file=sys.stderr)  # Newline

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Export the compatibility objects
colorama = _MockColorama()
tqdm = MockTqdm
init = colorama_init
