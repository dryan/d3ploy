"""
Tests for d3ploy configuration module.

Tests config loading, validation, migration, and merging.
"""

import json
from pathlib import Path

import pytest

from d3ploy.config import load_config
from d3ploy.config import load_env_vars
from d3ploy.config import merge_config
from d3ploy.config import migrate_config
from d3ploy.config import validate_config

# Path to config fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "configs"


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Fixture that provides a temporary directory and changes to it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_merge_config():
    """Test that config merging follows correct priority order."""
    defaults = {"bucket_name": "default-bucket", "acl": "private"}
    file_config = {"bucket_name": "file-bucket"}
    env_config = {"bucket_name": "env-bucket"}
    cli_args = {"bucket_name": "cli-bucket", "force": True}

    # Test priority: CLI > Env > File > Defaults
    merged = merge_config(defaults, file_config, env_config, cli_args)
    assert merged["bucket_name"] == "cli-bucket"
    assert merged["acl"] == "private"
    assert merged["force"] is True

    # Test priority: Env > File > Defaults
    merged = merge_config(defaults, file_config, env_config, {})
    assert merged["bucket_name"] == "env-bucket"

    # Test priority: File > Defaults
    merged = merge_config(defaults, file_config, {}, {})
    assert merged["bucket_name"] == "file-bucket"

    # Test priority: Defaults
    merged = merge_config(defaults, {}, {}, {})
    assert merged["bucket_name"] == "default-bucket"


def test_load_config_d3ploy_json(temp_config_dir):
    """Test loading from d3ploy.json file."""
    config_data = {"targets": {"default": {"bucket_name": "test"}}}
    (temp_config_dir / "d3ploy.json").write_text(json.dumps(config_data))

    loaded = load_config()
    assert loaded == config_data


def test_load_config_dot_d3ploy_json(temp_config_dir):
    """Test loading from .d3ploy.json file."""
    config_data = {"targets": {"default": {"bucket_name": "test"}}}
    (temp_config_dir / ".d3ploy.json").write_text(json.dumps(config_data))

    loaded = load_config()
    assert loaded == config_data


def test_load_config_explicit_path(temp_config_dir):
    """Test loading from explicitly specified config file."""
    config_data = {"targets": {"default": {"bucket_name": "test"}}}
    (temp_config_dir / "custom.json").write_text(json.dumps(config_data))

    loaded = load_config("custom.json")
    assert loaded == config_data


def test_validate_config_valid():
    """Test validation of a valid config."""
    config_data = {"targets": {"default": {}}}
    validated = validate_config(config_data)
    assert validated == config_data


def test_validate_config_invalid_type():
    """Test that invalid config type raises error."""
    with pytest.raises(ValueError):
        validate_config({"invalid": "structure"})


def test_validate_config_missing_environments():
    """Test that missing targets/environments key raises error."""
    with pytest.raises(ValueError):
        validate_config({"defaults": {}})


def test_migrate_config_v0_to_v2():
    """Test migration from v0 (no version field) to v2."""
    v0_config = {"environments": {}}
    migrated = migrate_config(v0_config)
    assert migrated["version"] == 2
    assert migrated["targets"] == {}
    assert "environments" not in migrated


def test_migrate_config_v1_to_v2():
    """Test migration from v1 to v2."""
    v1_config = {"version": 1, "environments": {"default": {}}}
    migrated = migrate_config(v1_config)
    assert migrated["version"] == 2
    assert migrated["targets"] == {"default": {}}
    assert "environments" not in migrated


def test_migrate_config_v2_no_change():
    """Test that v2 config is not modified."""
    v2_config = {"version": 2, "targets": {"default": {}}}
    migrated = migrate_config(v2_config)
    assert migrated == v2_config


def test_validate_config_recommended_caches():
    """Test that 'recommended' caches value is expanded to dict."""
    config_data = {"targets": {"default": {"caches": "recommended"}}}
    validated = validate_config(config_data)
    assert isinstance(validated["targets"]["default"]["caches"], dict)
    assert validated["targets"]["default"]["caches"]["text/html"] == 0


def test_load_env_vars(monkeypatch):
    """Test loading configuration from environment variables."""
    monkeypatch.setenv("D3PLOY_BUCKET_NAME", "env-bucket")
    monkeypatch.setenv("D3PLOY_PROCESSES", "20")

    env_vars = load_env_vars()
    assert env_vars["bucket_name"] == "env-bucket"
    assert env_vars["processes"] == 20


def test_migrate_v0_fixture():
    """Test migration using v0 fixture file."""
    v0_config = json.loads((FIXTURES_DIR / "v0-config.json").read_text())
    migrated = migrate_config(v0_config)

    # Should be upgraded to v2
    assert migrated["version"] == 2
    # Should have targets, not environments
    assert "targets" in migrated
    assert "environments" not in migrated
    # Should preserve all target configs
    assert "default" in migrated["targets"]
    assert "staging" in migrated["targets"]
    # Should preserve defaults
    assert "defaults" in migrated
    assert "caches" in migrated["defaults"]


def test_migrate_v1_fixture():
    """Test migration using v1 fixture file."""
    v1_config = json.loads((FIXTURES_DIR / "v1-config.json").read_text())
    migrated = migrate_config(v1_config)

    # Should be upgraded to v2
    assert migrated["version"] == 2
    # Should have targets, not environments
    assert "targets" in migrated
    assert "environments" not in migrated
    # Should preserve cloudfront_id
    assert migrated["targets"]["staging"]["cloudfront_id"] == "E1234567890ABC"


def test_v2_fixture_current():
    """Test that v2 fixture is already current version."""
    v2_config = json.loads((FIXTURES_DIR / "v2-config.json").read_text())
    migrated = migrate_config(v2_config)

    # Should be unchanged
    assert migrated == v2_config
    assert migrated["version"] == 2
