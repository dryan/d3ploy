#!/usr/bin/env python3
"""
Entry point for d3ploy when run as a module or Briefcase app.
"""

from .core.cli import cli

if __name__ == "__main__":
    cli()
