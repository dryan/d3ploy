"""
Tests for d3ploy.config.env module.
"""

from d3ploy.config import env


def test_load_env_vars_empty(monkeypatch):
    """Return empty dict when no D3PLOY_ vars are set."""
    # Clear any D3PLOY_ environment variables
    for key in list(monkeypatch._setitem):
        if key.startswith("D3PLOY_"):
            monkeypatch.delenv(key, raising=False)

    result = env.load_env_vars()
    assert result == {}


def test_load_env_vars_bucket_name(monkeypatch):
    """Load bucket_name from D3PLOY_BUCKET_NAME."""
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "my-bucket")

    result = env.load_env_vars()
    assert result["bucket_name"] == "my-bucket"


def test_load_env_vars_local_path(monkeypatch):
    """Load local_path from D3PLOY_LOCAL_PATH."""
    monkeypatch.setenv("D3PLOY_LOCAL_PATH", "/path/to/files")

    result = env.load_env_vars()
    assert result["local_path"] == "/path/to/files"


def test_load_env_vars_bucket_path(monkeypatch):
    """Load bucket_path from D3PLOY_BUCKET_PATH."""
    monkeypatch.setenv("D3PLOY_BUCKET_PATH", "prefix/path")

    result = env.load_env_vars()
    assert result["bucket_path"] == "prefix/path"


def test_load_env_vars_acl(monkeypatch):
    """Load acl from D3PLOY_ACL."""
    monkeypatch.setenv("D3PLOY_ACL", "public-read")

    result = env.load_env_vars()
    assert result["acl"] == "public-read"


def test_load_env_vars_charset(monkeypatch):
    """Load charset from D3PLOY_CHARSET."""
    monkeypatch.setenv("D3PLOY_CHARSET", "UTF-8")

    result = env.load_env_vars()
    assert result["charset"] == "UTF-8"


def test_load_env_vars_processes_valid_int(monkeypatch):
    """Load processes as integer from D3PLOY_PROCESSES."""
    monkeypatch.setenv("D3PLOY_PROCESSES", "20")

    result = env.load_env_vars()
    assert result["processes"] == 20
    assert isinstance(result["processes"], int)


def test_load_env_vars_processes_invalid_int(monkeypatch):
    """Invalid integer for D3PLOY_PROCESSES still sets string value."""
    monkeypatch.setenv("D3PLOY_PROCESSES", "not-a-number")

    result = env.load_env_vars()
    # Should still set the string value (not converted to int)
    assert result["processes"] == "not-a-number"


def test_load_env_vars_processes_zero(monkeypatch):
    """Load processes as zero."""
    monkeypatch.setenv("D3PLOY_PROCESSES", "0")

    result = env.load_env_vars()
    assert result["processes"] == 0


def test_load_env_vars_processes_negative(monkeypatch):
    """Load negative processes value (validation happens elsewhere)."""
    monkeypatch.setenv("D3PLOY_PROCESSES", "-5")

    result = env.load_env_vars()
    assert result["processes"] == -5


def test_load_env_vars_multiple(monkeypatch):
    """Load multiple environment variables."""
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("D3PLOY_LOCAL_PATH", "/local")
    monkeypatch.setenv("D3PLOY_ACL", "private")
    monkeypatch.setenv("D3PLOY_PROCESSES", "10")

    result = env.load_env_vars()

    assert result["bucket_name"] == "test-bucket"
    assert result["local_path"] == "/local"
    assert result["acl"] == "private"
    assert result["processes"] == 10


def test_load_env_vars_ignores_other_vars(monkeypatch):
    """Ignore environment variables without D3PLOY_ prefix."""
    monkeypatch.setenv("BUCKET_NAME", "should-be-ignored")
    monkeypatch.setenv("PATH", "/usr/bin")

    result = env.load_env_vars()

    assert "BUCKET_NAME" not in result
    assert "PATH" not in result
    assert result == {}


def test_load_env_vars_case_sensitive(monkeypatch):
    """Environment variable names are case-sensitive."""
    monkeypatch.setenv("d3ploy_bucket_name", "lowercase")  # Wrong case
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "uppercase")  # Correct case

    result = env.load_env_vars()

    assert result["bucket_name"] == "uppercase"


def test_env_mapping_constant():
    """Verify ENV_MAPPING has expected keys."""
    expected_keys = [
        "BUCKET_NAME",
        "LOCAL_PATH",
        "BUCKET_PATH",
        "ACL",
        "CHARSET",
        "PROCESSES",
    ]

    assert all(key in env.ENV_MAPPING for key in expected_keys)


def test_prefix_constant():
    """Verify PREFIX is set correctly."""
    assert env.PREFIX == "D3PLOY_"


def test_load_env_vars_with_empty_string_value(monkeypatch):
    """Load empty string values from environment."""
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "")

    result = env.load_env_vars()

    assert result["bucket_name"] == ""


def test_load_env_vars_with_spaces(monkeypatch):
    """Preserve spaces in environment variable values."""
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "bucket with spaces")

    result = env.load_env_vars()

    assert result["bucket_name"] == "bucket with spaces"


def test_load_env_vars_with_special_chars(monkeypatch):
    """Load values with special characters."""
    monkeypatch.setenv("D3PLOY_BUCKET_PATH", "path/with-special_chars.123")

    result = env.load_env_vars()

    assert result["bucket_path"] == "path/with-special_chars.123"
