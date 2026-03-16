"""
Tests for d3ploy.config.merger module.
"""

from d3ploy.config import merger


def test_merge_config_empty():
    """Merge empty configs returns empty result."""
    result = merger.merge_config({}, {}, {}, {})
    assert result == {}


def test_merge_config_defaults_only():
    """Use defaults when other sources are empty."""
    defaults = {"bucket_name": "default-bucket", "acl": "private"}
    result = merger.merge_config(defaults, {}, {}, {})

    assert result == defaults


def test_merge_config_file_overrides_defaults():
    """File config overrides defaults."""
    defaults = {"bucket_name": "default", "acl": "private"}
    file_config = {"bucket_name": "file-bucket"}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["bucket_name"] == "file-bucket"
    assert result["acl"] == "private"


def test_merge_config_env_overrides_file():
    """Environment config overrides file config."""
    defaults = {"bucket_name": "default"}
    file_config = {"bucket_name": "file-bucket"}
    env_config = {"bucket_name": "env-bucket"}

    result = merger.merge_config(defaults, file_config, env_config, {})

    assert result["bucket_name"] == "env-bucket"


def test_merge_config_cli_overrides_all():
    """CLI args override all other sources."""
    defaults = {"bucket_name": "default"}
    file_config = {"bucket_name": "file-bucket"}
    env_config = {"bucket_name": "env-bucket"}
    cli_args = {"bucket_name": "cli-bucket"}

    result = merger.merge_config(defaults, file_config, env_config, cli_args)

    assert result["bucket_name"] == "cli-bucket"


def test_merge_config_priority_order():
    """Verify complete priority order: CLI > Env > File > Defaults."""
    defaults = {
        "bucket_name": "default",
        "acl": "private",
        "processes": 5,
        "force": False,
    }
    file_config = {
        "bucket_name": "file-bucket",
        "acl": "public-read",
    }
    env_config = {
        "bucket_name": "env-bucket",
    }
    cli_args = {
        "force": True,
    }

    result = merger.merge_config(defaults, file_config, env_config, cli_args)

    # CLI wins for force
    assert result["force"] is True
    # Env wins for bucket_name
    assert result["bucket_name"] == "env-bucket"
    # File wins for acl
    assert result["acl"] == "public-read"
    # Defaults win for processes
    assert result["processes"] == 5


def test_merge_config_ignores_none_values():
    """Don't override with None values."""
    defaults = {"bucket_name": "default", "acl": "private"}
    file_config = {"bucket_name": "file-bucket", "acl": None}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["bucket_name"] == "file-bucket"
    assert result["acl"] == "private"  # None didn't override


def test_merge_config_allows_false_values():
    """Allow False boolean values to override."""
    defaults = {"force": True, "dry_run": True}
    cli_args = {"force": False}

    result = merger.merge_config(defaults, {}, {}, cli_args)

    assert result["force"] is False
    assert result["dry_run"] is True


def test_merge_config_allows_zero_values():
    """Allow 0 numeric values to override."""
    defaults = {"processes": 10}
    file_config = {"processes": 0}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["processes"] == 0


def test_merge_config_allows_empty_string():
    """Allow empty string values to override."""
    defaults = {"bucket_path": "default/path"}
    file_config = {"bucket_path": ""}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["bucket_path"] == ""


def test_merge_config_new_keys_from_file():
    """Add new keys from file config."""
    defaults = {"bucket_name": "default"}
    file_config = {"local_path": "/path/to/files"}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["bucket_name"] == "default"
    assert result["local_path"] == "/path/to/files"


def test_merge_config_new_keys_from_cli():
    """Add new keys from CLI args."""
    defaults = {"bucket_name": "default"}
    cli_args = {"verbose": True}

    result = merger.merge_config(defaults, {}, {}, cli_args)

    assert result["bucket_name"] == "default"
    assert result["verbose"] is True


def test_merge_config_complex_values():
    """Merge complex value types (lists, dicts)."""
    defaults = {
        "excludes": [".git", ".DS_Store"],
        "caches": {"text/html": 0},
    }
    file_config = {
        "excludes": ["node_modules"],
        "caches": {"text/css": 31536000},
    }

    result = merger.merge_config(defaults, file_config, {}, {})

    # Complex values are replaced, not merged
    assert result["excludes"] == ["node_modules"]
    assert result["caches"] == {"text/css": 31536000}


def test_merge_config_doesnt_mutate_defaults():
    """Merging doesn't mutate the defaults dict."""
    defaults = {"bucket_name": "default"}
    original = defaults.copy()

    merger.merge_config(defaults, {"bucket_name": "changed"}, {}, {})

    assert defaults == original


def test_merge_config_all_sources_empty():
    """Handle all sources being empty dicts."""
    result = merger.merge_config({}, {}, {}, {})
    assert result == {}


def test_merge_config_with_list_values():
    """Handle list values in config."""
    defaults = {"excludes": [".git"]}
    file_config = {"excludes": [".git", "node_modules"]}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["excludes"] == [".git", "node_modules"]


def test_merge_config_with_nested_dicts():
    """Handle nested dict values."""
    defaults = {"caches": {"text/html": 0}}
    file_config = {"caches": {"text/html": 3600, "text/css": 31536000}}

    result = merger.merge_config(defaults, file_config, {}, {})

    assert result["caches"]["text/html"] == 3600
    assert result["caches"]["text/css"] == 31536000
