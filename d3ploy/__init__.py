"""
d3ploy - Deploy static files to AWS S3 with CloudFront invalidation.
"""

__version__ = "4.4.3"

from .core.cli import cli

__all__ = ["cli", "__version__"]
