#!/usr/bin/env python3
"""
Legacy entry point for d3ploy.

This module maintains backward compatibility with older code that imports
from d3ploy.d3ploy. New code should import from the appropriate submodules.
"""

import mimetypes

from . import __version__
from .compat import init as colorama_init
from .core.cli import cli

# Legacy constants for backward compatibility
VERSION = __version__

# From https://mzl.la/39XkRvH
MIMETYPES = {
    "application/manifest+json": [".webmanifest"],
    "application/ogg": [".ogg"],
    "audio/wave": [".wav"],
    "font/otf": [".otf"],
    "font/ttf": [".ttf"],
    "font/woff": [".woff"],
    "font/woff2": [".woff2"],
    "image/apng": [".apng"],
    "image/avif": [".avif"],
    "image/bmp": [".bmp"],
    "image/gif": [".gif"],
    "image/jpeg": [".jpeg", ".jpg", ".jfif", ".pjpeg", ".pjp"],
    "image/jxl": [".jxl"],
    "image/png": [".png"],
    "image/svg+xml": [".svg"],
    "image/tiff": [".tif", ".tiff"],
    "image/webp": [".webp"],
    "image/x-icon": [".ico", ".cur"],
    "text/css": [".css"],
    "text/html": [".html", ".htm"],
    "text/javascript": [".js", ".mjs"],
    "text/plain": [".txt"],
    "video/webm": [".webm"],
}

# Register custom MIME types
for mimetype in MIMETYPES:
    for extension in MIMETYPES[mimetype]:
        mimetypes.add_type(mimetype, extension)


if __name__ == "__main__":
    colorama_init()
    cli()
