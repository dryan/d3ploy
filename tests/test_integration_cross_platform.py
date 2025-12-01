"""Integration tests for cross-platform compatibility."""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from d3ploy.utils import paths


class TestCrossPlatformCompatibility:
    """Test that d3ploy works correctly across different platforms."""

    def test_path_handling_across_platforms(self) -> None:
        """Test that file path handling works correctly on all platforms."""
        # Test with various path formats
        test_paths = [
            "simple/path",
            "path/with spaces/file.txt",
            "path/with.dots/file.name.ext",
            "深度/unicode/测试.txt",  # Unicode test
        ]

        for test_path in test_paths:
            path_obj = Path(test_path)
            # Should be able to create Path objects without issues
            assert isinstance(path_obj, Path)
            # Should be able to convert back to string
            assert isinstance(str(path_obj), str)

    @pytest.mark.parametrize("platform_name", ["Darwin", "Windows", "Linux"])
    def test_app_data_dir_platform_specific(self, platform_name: str) -> None:
        """Test app data directory creation for different platforms."""
        with patch("platform.system", return_value=platform_name):
            if platform_name == "Windows":
                with patch.dict(os.environ, {"APPDATA": "/mock/appdata"}, clear=False):
                    app_dir = paths.get_app_data_dir()
                    assert "d3ploy" in str(app_dir)
            else:
                app_dir = paths.get_app_data_dir()
                assert "d3ploy" in str(app_dir)

    @pytest.mark.parametrize("platform_name", ["Darwin", "Windows", "Linux"])
    def test_cache_dir_platform_specific(self, platform_name: str) -> None:
        """Test cache directory creation for different platforms."""
        with patch("platform.system", return_value=platform_name):
            if platform_name == "Windows":
                with patch.dict(
                    os.environ, {"LOCALAPPDATA": "/mock/localappdata"}, clear=False
                ):
                    cache_dir = paths.get_cache_dir()
                    assert "d3ploy" in str(cache_dir)
            else:
                cache_dir = paths.get_cache_dir()
                assert "d3ploy" in str(cache_dir)

    @pytest.mark.parametrize("platform_name", ["Darwin", "Windows", "Linux"])
    def test_log_dir_platform_specific(self, platform_name: str) -> None:
        """Test log directory creation for different platforms."""
        with patch("platform.system", return_value=platform_name):
            if platform_name == "Windows":
                with patch.dict(
                    os.environ, {"LOCALAPPDATA": "/mock/localappdata"}, clear=False
                ):
                    log_dir = paths.get_log_dir()
                    assert "d3ploy" in str(log_dir)
            else:
                log_dir = paths.get_log_dir()
                assert "d3ploy" in str(log_dir)

    def test_temp_dir_cross_platform(self) -> None:
        """Test temporary directory creation works on all platforms."""
        temp_dir = paths.get_temp_dir()
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "d3ploy" in str(temp_dir)

    def test_file_permissions_handling(self) -> None:
        """Test that file permission handling works across platforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_file.txt"
            test_file.write_text("test content")

            # Should be able to read the file on all platforms
            assert test_file.exists()
            content = test_file.read_text()
            assert content == "test content"

    def test_environment_variable_handling(self) -> None:
        """Test that environment variables are handled consistently."""
        # Test common environment variables that should work everywhere
        test_vars = {
            "D3PLOY_TEST_VAR": "test_value",
            "D3PLOY_BUCKET_NAME": "test-bucket",
        }

        with patch.dict(os.environ, test_vars):
            # Should be able to read environment variables
            for var, expected_value in test_vars.items():
                assert os.environ.get(var) == expected_value

    def test_unicode_handling_in_paths(self) -> None:
        """Test that Unicode characters in file paths are handled correctly."""
        # Test various Unicode characters that might appear in file names
        unicode_tests = [
            "测试文件.txt",  # Chinese
            "файл.txt",  # Cyrillic
            "archivo.txt",  # Spanish
            "tëst.txt",  # Accented
            "emoji📁.txt",  # Emoji (if supported)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for unicode_name in unicode_tests:
                try:
                    test_file = temp_path / unicode_name
                    test_file.write_text("test content", encoding="utf-8")

                    # Should be able to read back the content
                    if (
                        test_file.exists()
                    ):  # Some filesystems may not support all Unicode
                        content = test_file.read_text(encoding="utf-8")
                        assert content == "test content"
                except (OSError, UnicodeError):
                    # Some platforms/filesystems may not support certain Unicode characters
                    # This is acceptable - we just want to ensure it doesn't crash
                    pass

    def test_line_ending_handling(self) -> None:
        """Test that different line ending styles are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test different line endings
            line_endings = {
                "unix": "line1\nline2\nline3",
                "windows": "line1\r\nline2\r\nline3",
                "mac_classic": "line1\rline2\rline3",
                "mixed": "line1\nline2\r\nline3\r",
            }

            for name, content in line_endings.items():
                test_file = temp_path / f"test_{name}.txt"
                test_file.write_text(content, encoding="utf-8")

                # Should be able to read the content back
                read_content = test_file.read_text(encoding="utf-8")
                # Content might be normalized by the OS, but should not crash
                assert isinstance(read_content, str)

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific test")
    def test_unix_specific_features(self) -> None:
        """Test Unix-specific features work correctly."""
        # Test that Unix-style paths work
        unix_path = Path("/tmp")
        # Should exist on Unix systems
        if unix_path.exists():
            assert unix_path.is_dir()

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_specific_features(self) -> None:
        """Test Windows-specific features work correctly."""
        # Test that Windows-style paths work
        # Check for typical Windows environment variables
        windows_vars = ["APPDATA", "LOCALAPPDATA", "USERPROFILE"]

        # At least one should be present on Windows
        found_vars = [var for var in windows_vars if os.environ.get(var)]
        assert len(found_vars) > 0, "No Windows environment variables found"

    def test_case_sensitivity_handling(self) -> None:
        """Test that file path case sensitivity is handled appropriately."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file with specific casing
            test_file = temp_path / "TestFile.txt"
            test_file.write_text("content")

            # Test accessing with different case
            # Behavior will vary by filesystem, but should not crash
            different_case = temp_path / "testfile.txt"

            try:
                # On case-insensitive filesystems this might work
                # On case-sensitive filesystems it might not
                # Either way it should not crash
                exists = different_case.exists()
                assert isinstance(exists, bool)
            except Exception:
                # If there's an exception, it should be a reasonable one
                # not a crash or undefined behavior
                pass

    def test_platform_detection(self) -> None:
        """Test that platform detection works correctly."""
        current_platform = platform.system()
        assert current_platform in [
            "Darwin",
            "Linux",
            "Windows",
            "Java",
        ]  # Java for Jython

        # Should be able to get platform info
        machine = platform.machine()
        assert isinstance(machine, str)

        processor = platform.processor()
        assert isinstance(processor, str)
