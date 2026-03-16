"""
Tests for MIME type utilities.
"""

import mimetypes
from pathlib import Path

from d3ploy.utils import mimetypes as mimetype_utils


def test_register_custom_types():
    """Test that register_custom_types adds custom MIME types."""
    # Register the custom types
    mimetype_utils.register_custom_types()

    # Test some custom types were registered
    assert mimetypes.guess_type("test.webmanifest")[0] == "application/manifest+json"
    assert mimetypes.guess_type("test.woff2")[0] == "font/woff2"
    assert mimetypes.guess_type("test.avif")[0] == "image/avif"
    assert mimetypes.guess_type("test.mjs")[0] == "text/javascript"


def test_get_content_type_known_extension():
    """Test get_content_type with known file extension."""
    # Register custom types first
    mimetype_utils.register_custom_types()

    # Test various file types
    assert mimetype_utils.get_content_type(Path("test.html")) == "text/html"
    assert mimetype_utils.get_content_type(Path("test.css")) == "text/css"
    assert mimetype_utils.get_content_type(Path("test.js")) == "text/javascript"
    assert mimetype_utils.get_content_type(Path("test.png")) == "image/png"
    assert mimetype_utils.get_content_type(Path("test.woff2")) == "font/woff2"


def test_get_content_type_with_charset():
    """Test get_content_type with charset parameter."""
    mimetype_utils.register_custom_types()

    result = mimetype_utils.get_content_type(Path("test.html"), charset="utf-8")
    assert result == "text/html; charset=utf-8"

    result = mimetype_utils.get_content_type(Path("test.css"), charset="utf-8")
    assert result == "text/css; charset=utf-8"


def test_get_content_type_unknown_extension():
    """Test get_content_type with unknown file extension."""
    result = mimetype_utils.get_content_type(Path("test.unknown"))
    assert result == "application/octet-stream"


def test_get_content_type_unknown_with_charset():
    """Test get_content_type with unknown extension and charset."""
    result = mimetype_utils.get_content_type(
        Path("test.unknownext123"), charset="utf-8"
    )
    assert result == "application/octet-stream; charset=utf-8"
