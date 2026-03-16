"""
Tests for d3ploy.config.migration module.
"""

import json

import pytest

from d3ploy.config import migration


def test_migrate_config_v0_to_v1():
    """Migrate from v0 (no version) to v1 (add version field)."""
    v0_config = {"environments": {"default": {}}}
    result = migration.migrate_config(v0_config)

    assert result["version"] >= 1


def test_migrate_config_v0_to_v2():
    """Migrate from v0 directly to v2 (current)."""
    v0_config = {"environments": {"default": {"bucket_name": "test"}}}
    result = migration.migrate_config(v0_config)

    assert result["version"] == 2
    assert "targets" in result
    assert "environments" not in result
    assert result["targets"]["default"]["bucket_name"] == "test"


def test_migrate_config_v1_to_v2():
    """Migrate from v1 to v2 (rename environments to targets)."""
    v1_config = {
        "version": 1,
        "environments": {
            "prod": {"bucket_name": "prod-bucket"},
        },
    }
    result = migration.migrate_config(v1_config)

    assert result["version"] == 2
    assert "targets" in result
    assert "environments" not in result
    assert result["targets"]["prod"]["bucket_name"] == "prod-bucket"


def test_migrate_config_v2_no_change():
    """Don't modify v2 config (current version)."""
    v2_config = {
        "version": 2,
        "targets": {"default": {"bucket_name": "test"}},
    }
    result = migration.migrate_config(v2_config)

    assert result == v2_config


def test_migrate_config_preserves_defaults():
    """Migration preserves defaults section."""
    v0_config = {
        "environments": {"default": {}},
        "defaults": {"acl": "private", "processes": 10},
    }
    result = migration.migrate_config(v0_config)

    assert result["defaults"]["acl"] == "private"
    assert result["defaults"]["processes"] == 10


def test_migrate_config_preserves_all_targets():
    """Migration preserves all targets."""
    v1_config = {
        "version": 1,
        "environments": {
            "dev": {"bucket_name": "dev"},
            "staging": {"bucket_name": "staging"},
            "prod": {"bucket_name": "prod"},
        },
    }
    result = migration.migrate_config(v1_config)

    assert len(result["targets"]) == 3
    assert "dev" in result["targets"]
    assert "staging" in result["targets"]
    assert "prod" in result["targets"]


def test_migrate_config_v1_without_environments_key():
    """Handle v1 config without environments key."""
    v1_config = {"version": 1, "defaults": {"acl": "private"}}
    result = migration.migrate_config(v1_config)

    assert result["version"] == 2
    assert "environments" not in result
    # Should have targets even if empty (or not present)


def test_migrate_config_future_version():
    """Raise ValueError for future version."""
    future_config = {"version": 999}

    with pytest.raises(ValueError, match="is newer than supported"):
        migration.migrate_config(future_config)


def test_migrate_config_doesnt_mutate_input():
    """Migration doesn't mutate the input dict."""
    v0_config = {"environments": {"default": {}}}
    original = v0_config.copy()

    migration.migrate_config(v0_config)

    assert v0_config == original


def test_needs_migration_v0():
    """needs_migration returns True for v0."""
    assert migration.needs_migration({"environments": {}}) is True


def test_needs_migration_v1():
    """needs_migration returns True for v1."""
    assert migration.needs_migration({"version": 1}) is True


def test_needs_migration_v2():
    """needs_migration returns False for v2 (current)."""
    assert migration.needs_migration({"version": 2}) is False


def test_needs_migration_future_version():
    """needs_migration returns False for future versions."""
    assert migration.needs_migration({"version": 999}) is False


def test_save_migrated_config(tmp_path):
    """Save migrated config to disk."""
    config = {"version": 2, "targets": {"default": {}}}
    config_path = tmp_path / "migrated.json"

    migration.save_migrated_config(config, path=str(config_path))

    assert config_path.exists()
    loaded = json.loads(config_path.read_text())
    assert loaded == config


def test_save_migrated_config_formatting(tmp_path):
    """Saved config has proper formatting."""
    config = {
        "version": 2,
        "targets": {"default": {"bucket_name": "test"}},
    }
    config_path = tmp_path / "formatted.json"

    migration.save_migrated_config(config, path=str(config_path))

    content = config_path.read_text()
    # Should be indented
    assert "  " in content
    # Should have trailing newline
    assert content.endswith("\n")


def test_save_migrated_config_creates_parent_dirs(tmp_path):
    """save_migrated_config creates parent directories."""
    config = {"version": 2, "targets": {}}
    config_path = tmp_path / "nested" / "path" / "config.json"

    migration.save_migrated_config(config, path=str(config_path))

    assert config_path.exists()
    assert config_path.parent.exists()


def test_get_migration_command_default():
    """get_migration_command returns default command."""
    cmd = migration.get_migration_command()
    assert cmd == "d3ploy --migrate-config .d3ploy.json"


def test_get_migration_command_custom_path():
    """get_migration_command with custom path."""
    cmd = migration.get_migration_command("custom.json")
    assert cmd == "d3ploy --migrate-config custom.json"


def test_current_version_constant():
    """Verify CURRENT_VERSION is set correctly."""
    assert migration.CURRENT_VERSION == 2
    assert isinstance(migration.CURRENT_VERSION, int)


def test_migrate_config_preserves_caches():
    """Migration preserves caches configuration."""
    v0_config = {
        "environments": {
            "default": {
                "caches": {"text/html": 0, "text/css": 31536000},
            },
        },
    }
    result = migration.migrate_config(v0_config)

    assert result["targets"]["default"]["caches"]["text/html"] == 0
    assert result["targets"]["default"]["caches"]["text/css"] == 31536000


def test_migrate_config_preserves_cloudfront_id():
    """Migration preserves cloudfront_id."""
    v1_config = {
        "version": 1,
        "environments": {
            "prod": {"cloudfront_id": "E123456"},
        },
    }
    result = migration.migrate_config(v1_config)

    assert result["targets"]["prod"]["cloudfront_id"] == "E123456"


def test_save_migrated_config_permission_error(tmp_path):
    """Raise PermissionError when path is not writable."""
    config = {"version": 2, "targets": {}}
    config_path = tmp_path / "readonly.json"
    config_path.touch()
    config_path.chmod(0o444)

    try:
        with pytest.raises(PermissionError):
            migration.save_migrated_config(config, path=str(config_path))
    finally:
        # Cleanup
        config_path.chmod(0o644)
