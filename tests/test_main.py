"""
Tests for d3ploy.__main__ module.
"""

import subprocess


def test_main_module_imports():
    """Test that __main__ module can be imported."""
    import d3ploy.__main__  # noqa: F401


def test_main_via_python_m():
    """Test running d3ploy as a module with python -m."""
    result = subprocess.run(
        ["python", "-m", "d3ploy", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "d3ploy" in result.stdout.lower() or "usage" in result.stdout.lower()
