"""
MIME type detection utilities.
"""

import mimetypes
from pathlib import Path
from typing import Optional

# Custom MIME types from https://mzl.la/39XkRvH
CUSTOM_MIMETYPES = {
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


def register_custom_types() -> None:
    """
    Register custom MIME type mappings.

    Adds additional MIME types not in standard library.
    This should be called once during application initialization.
    """
    for mimetype, extensions in CUSTOM_MIMETYPES.items():
        for extension in extensions:
            mimetypes.add_type(mimetype, extension)


def get_content_type(file: Path, *, charset: Optional[str] = None) -> str:
    """
    Get Content-Type header value for file.

    Args:
        file: File path.
        charset: Optional charset to append (e.g., "utf-8").

    Returns:
        Full Content-Type header value.
    """
    # Guess the MIME type based on file extension
    content_type, _ = mimetypes.guess_type(str(file))

    # Default to application/octet-stream if unknown
    if content_type is None:
        content_type = "application/octet-stream"

    # Append charset if provided
    if charset:
        content_type = f"{content_type}; charset={charset}"

    return content_type
