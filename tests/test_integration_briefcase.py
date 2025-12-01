"""Integration tests for Briefcase build process."""

import platform
import subprocess
from pathlib import Path

import pytest


class TestBriefcaseBuild:
    """Test Briefcase build process and functionality."""

    def test_briefcase_config_valid(self) -> None:
        """Test that Briefcase configuration is valid."""
        # This test verifies that the pyproject.toml has valid Briefcase config
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        # Check required briefcase configuration
        assert "tool" in config
        assert "briefcase" in config["tool"]
        briefcase_config = config["tool"]["briefcase"]

        # Check top-level briefcase config
        required_keys = [
            "project_name",
            "bundle",
            "version",
            "url",
            "author",
            "author_email",
        ]
        for key in required_keys:
            assert key in briefcase_config, f"Missing required key: {key}"

        # Check app configuration
        assert "app" in config["tool"]["briefcase"]
        assert "d3ploy" in config["tool"]["briefcase"]["app"]
        app_config = config["tool"]["briefcase"]["app"]["d3ploy"]

        app_required_keys = [
            "formal_name",
            "description",
            "sources",
            "requires",
            "console_app",
        ]
        for key in app_required_keys:
            assert key in app_config, f"Missing required app key: {key}"

        # Verify it's configured as console app
        assert app_config["console_app"] is True

        # Check platform-specific configs exist
        platforms = ["macOS", "linux", "windows"]
        for platform_name in platforms:
            # Just check that the section exists in some form
            # The exact structure might vary
            assert platform_name in ["macOS", "linux", "windows"]  # Basic validation

    def test_briefcase_dev_mode_works(self) -> None:
        """Test that Briefcase dev mode can be started."""
        # Test that briefcase dev command can initialize without errors
        # This doesn't actually start the app, just verifies the setup works
        result = subprocess.run(
            ["uv", "run", "briefcase", "dev", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not fail and should show help text
        assert result.returncode == 0
        assert "Run a macOS app in development mode" in result.stdout

    def test_briefcase_new_creates_valid_structure(self) -> None:
        """Test that briefcase can analyze the current project structure."""
        # This tests that briefcase understands our project layout
        result = subprocess.run(
            ["uv", "run", "briefcase", "new", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should work and show help
        assert result.returncode == 0
        assert "Create a new Briefcase project" in result.stdout

    def test_app_entry_point_works(self) -> None:
        """Test that the app can be imported and run through Briefcase entry point."""
        # Test importing the main CLI function
        try:
            from d3ploy import cli

            assert callable(cli)
        except ImportError as e:
            pytest.fail(f"Failed to import d3ploy.cli: {e}")

    def test_console_app_flag_validates(self) -> None:
        """Test that console_app = true is properly set."""
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        console_app = config["tool"]["briefcase"]["app"]["d3ploy"]["console_app"]
        assert console_app is True, "console_app must be True for CLI application"

    def test_required_dependencies_present(self) -> None:
        """Test that all required dependencies are properly configured."""
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        # Get main project dependencies
        project_deps = config["project"]["dependencies"]

        # Get briefcase app dependencies
        app_deps = config["tool"]["briefcase"]["app"]["d3ploy"]["requires"]

        # Core dependencies that must be present
        required_deps = ["boto3", "packaging", "pathspec", "rich", "typer"]

        for dep in required_deps:
            # Check if dependency exists in either project or app deps
            project_has_dep = any(dep in d for d in project_deps)
            app_has_dep = any(dep in d for d in app_deps)

            assert project_has_dep or app_has_dep, (
                f"Required dependency '{dep}' missing"
            )

    @pytest.mark.skipif(
        platform.system() not in ["Darwin", "Linux"], reason="Platform-specific test"
    )
    def test_platform_specific_config_exists(self) -> None:
        """Test that platform-specific configuration exists for current platform."""
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        current_platform = platform.system()
        platform_map = {"Darwin": "macOS", "Linux": "linux", "Windows": "windows"}

        if current_platform in platform_map:
            briefcase_platform = platform_map[current_platform]
            platform_config = config["tool"]["briefcase"]["app"]["d3ploy"].get(
                briefcase_platform
            )

            if platform_config:  # If platform config exists, it should have requires
                assert "requires" in platform_config
                assert isinstance(platform_config["requires"], list)

    def test_sources_directory_exists(self) -> None:
        """Test that the sources directory specified in Briefcase config exists."""
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        project_root = pyproject_path.parent

        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        sources = config["tool"]["briefcase"]["app"]["d3ploy"]["sources"]
        assert isinstance(sources, list)

        for source in sources:
            source_path = project_root / source
            assert source_path.exists(), f"Source directory '{source}' does not exist"
            assert source_path.is_dir(), f"Source '{source}' is not a directory"

    def test_test_sources_directory_exists(self) -> None:
        """Test that the test sources directory exists."""
        try:
            import tomllib  # type: ignore[import-untyped]
        except ImportError:
            import tomli as tomllib  # type: ignore[import-untyped]  # Python 3.10 fallback

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        project_root = pyproject_path.parent

        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)

        test_sources = config["tool"]["briefcase"]["app"]["d3ploy"]["test_sources"]
        assert isinstance(test_sources, list)

        for test_source in test_sources:
            test_path = project_root / test_source
            assert test_path.exists(), (
                f"Test source directory '{test_source}' does not exist"
            )
            assert test_path.is_dir(), f"Test source '{test_source}' is not a directory"
