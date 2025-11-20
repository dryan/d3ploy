"""
Tests for MIME type utilities.
"""

from pathlib import Path

import pytest

from d3ploy.utils import mimetypes


def test_register_custom_types_not_implemented():
    """Test that register_custom_types raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Phase 3.6"):
        mimetypes.register_custom_types()


def test_get_content_type_not_implemented():
    """Test that get_content_type raises NotImplementedError."""
    test_file = Path("test.txt")
    with pytest.raises(NotImplementedError, match="Phase 3.6"):
        mimetypes.get_content_type(test_file)


def test_get_content_type_with_charset_not_implemented():
    """Test that get_content_type with charset raises NotImplementedError."""
    test_file = Path("test.html")
    with pytest.raises(NotImplementedError, match="Phase 3.6"):
        mimetypes.get_content_type(test_file, charset="utf-8")
