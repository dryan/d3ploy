"""
Tests for d3ploy.config.loader module.
"""

import json

import pytest

from d3ploy.config import loader


def test_load_config_d3ploy_json(tmp_path, monkeypatch):
    """Load from d3ploy.json."""
    config_data = {"targets": {"default": {"bucket_name": "test"}}}
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text(json.dumps(config_data))

    monkeypatch.chdir(tmp_path)
    result = loader.load_config()

    assert result == config_data


def test_load_config_dot_d3ploy_json(tmp_path, monkeypatch):
    """Load from .d3ploy.json."""
    config_data = {"targets": {"default": {"bucket_name": "test"}}}
    config_file = tmp_path / ".d3ploy.json"
    config_file.write_text(json.dumps(config_data))

    monkeypatch.chdir(tmp_path)
    result = loader.load_config()

    assert result == config_data


def test_load_config_prefers_d3ploy_json(tmp_path, monkeypatch):
    """Prefer d3ploy.json over .d3ploy.json when both exist."""
    config1 = {"targets": {"default": {"bucket_name": "from-d3ploy"}}}
    config2 = {"targets": {"default": {"bucket_name": "from-dot-d3ploy"}}}

    (tmp_path / "d3ploy.json").write_text(json.dumps(config1))
    (tmp_path / ".d3ploy.json").write_text(json.dumps(config2))

    monkeypatch.chdir(tmp_path)
    result = loader.load_config()

    assert result == config1


def test_load_config_explicit_path(tmp_path):
    """Load from explicitly specified path."""
    config_data = {"targets": {"default": {"bucket_name": "custom"}}}
    config_file = tmp_path / "custom-config.json"
    config_file.write_text(json.dumps(config_data))

    result = loader.load_config(str(config_file))

    assert result == config_data


def test_load_config_explicit_path_not_found(tmp_path):
    """Raise FileNotFoundError when explicit path doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        loader.load_config(str(tmp_path / "nonexistent.json"))


def test_load_config_no_config_files(tmp_path, monkeypatch):
    """Raise FileNotFoundError when no config files exist."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="No config file found"):
        loader.load_config()


def test_load_config_invalid_json(tmp_path, monkeypatch):
    """Raise JSONDecodeError for invalid JSON."""
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text("{invalid json")

    monkeypatch.chdir(tmp_path)

    with pytest.raises(json.JSONDecodeError):
        loader.load_config()


def test_load_config_empty_file(tmp_path, monkeypatch):
    """Raise JSONDecodeError for empty file."""
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text("")

    monkeypatch.chdir(tmp_path)

    with pytest.raises(json.JSONDecodeError):
        loader.load_config()


def test_load_config_with_unicode(tmp_path, monkeypatch):
    """Load config with unicode characters."""
    config_data = {"targets": {"default": {"bucket_name": "test-🚀"}}}
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text(json.dumps(config_data, ensure_ascii=False))

    monkeypatch.chdir(tmp_path)
    result = loader.load_config()

    assert result == config_data


def test_load_config_with_nested_structure(tmp_path, monkeypatch):
    """Load config with deeply nested structure."""
    config_data = {
        "version": 2,
        "targets": {
            "prod": {
                "bucket_name": "prod-bucket",
                "caches": {
                    "text/html": 0,
                    "text/css": 31536000,
                },
            }
        },
        "defaults": {
            "acl": "private",
            "processes": 10,
        },
    }
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text(json.dumps(config_data))

    monkeypatch.chdir(tmp_path)
    result = loader.load_config()

    assert result == config_data


def test_load_config_permission_error(tmp_path, monkeypatch):
    """Raise PermissionError when file is not readable."""
    config_file = tmp_path / "d3ploy.json"
    config_file.write_text(json.dumps({"targets": {}}))
    config_file.chmod(0o000)

    monkeypatch.chdir(tmp_path)

    try:
        with pytest.raises(PermissionError):
            loader.load_config()
    finally:
        # Cleanup: restore permissions
        config_file.chmod(0o644)


def test_config_files_constant():
    """Verify CONFIG_FILES constant has expected values."""
    assert loader.CONFIG_FILES == ["d3ploy.json", ".d3ploy.json"]
