"""
Tests for d3ploy.config.validator module.
"""

import pytest

from d3ploy.config import validator
from d3ploy.config.constants import RECOMMENDED_CACHES


def test_validate_config_valid_minimal():
    """Validate minimal valid config."""
    config = {"targets": {"default": {}}}
    result = validator.validate_config(config)
    assert result == config


def test_validate_config_valid_with_defaults():
    """Validate config with defaults section."""
    config = {
        "targets": {"default": {}},
        "defaults": {"acl": "private"},
    }
    result = validator.validate_config(config)
    assert result == config


def test_validate_config_not_dict():
    """Raise ValueError for non-dict config."""
    with pytest.raises(ValueError, match="must be a dictionary"):
        validator.validate_config([])  # ty: ignore[invalid-argument-type]

    with pytest.raises(ValueError, match="must be a dictionary"):
        validator.validate_config("string")  # ty: ignore[invalid-argument-type]

    with pytest.raises(ValueError, match="must be a dictionary"):
        validator.validate_config(42)  # ty: ignore[invalid-argument-type]


def test_validate_config_missing_targets():
    """Raise ValueError when targets key is missing."""
    with pytest.raises(ValueError, match="missing 'targets' key"):
        validator.validate_config({"defaults": {}})

    with pytest.raises(ValueError, match="missing 'targets' key"):
        validator.validate_config({})


def test_validate_config_targets_not_dict():
    """Raise ValueError when targets is not a dict."""
    with pytest.raises(ValueError, match="'targets' must be a dictionary"):
        validator.validate_config({"targets": []})

    with pytest.raises(ValueError, match="'targets' must be a dictionary"):
        validator.validate_config({"targets": "string"})


def test_validate_config_defaults_not_dict():
    """Raise ValueError when defaults is not a dict."""
    with pytest.raises(ValueError, match="'defaults' must be a dictionary"):
        validator.validate_config(
            {
                "targets": {"default": {}},
                "defaults": [],
            }
        )


def test_validate_config_target_not_dict():
    """Raise ValueError when a target is not a dict."""
    with pytest.raises(ValueError, match="Target 'prod' must be a dictionary"):
        validator.validate_config(
            {
                "targets": {
                    "prod": "not a dict",
                },
            }
        )


def test_validate_config_expands_recommended_caches_in_target():
    """Expand 'recommended' caches in target."""
    config = {
        "targets": {
            "default": {"caches": "recommended"},
        },
    }
    result = validator.validate_config(config)

    assert result["targets"]["default"]["caches"] == RECOMMENDED_CACHES
    assert isinstance(result["targets"]["default"]["caches"], dict)


def test_validate_config_expands_recommended_caches_in_defaults():
    """Expand 'recommended' caches in defaults."""
    config = {
        "targets": {"default": {}},
        "defaults": {"caches": "recommended"},
    }
    result = validator.validate_config(config)

    assert result["defaults"]["caches"] == RECOMMENDED_CACHES
    assert isinstance(result["defaults"]["caches"], dict)


def test_validate_config_leaves_custom_caches():
    """Don't modify custom caches dict."""
    custom_caches = {"text/html": 3600}
    config = {
        "targets": {
            "default": {"caches": custom_caches},
        },
    }
    result = validator.validate_config(config)

    assert result["targets"]["default"]["caches"] == custom_caches


def test_validate_config_multiple_targets():
    """Validate config with multiple targets."""
    config = {
        "targets": {
            "dev": {"bucket_name": "dev-bucket"},
            "staging": {"bucket_name": "staging-bucket", "caches": "recommended"},
            "prod": {"bucket_name": "prod-bucket"},
        },
    }
    result = validator.validate_config(config)

    assert "dev" in result["targets"]
    assert "staging" in result["targets"]
    assert "prod" in result["targets"]
    # Check that recommended was expanded in staging
    assert result["targets"]["staging"]["caches"] == RECOMMENDED_CACHES


def test_validate_config_empty_targets():
    """Allow empty targets dict."""
    config = {"targets": {}}
    result = validator.validate_config(config)
    assert result == config


def test_expand_caches_modifies_in_place():
    """_expand_caches modifies the dict in place."""
    config = {"caches": "recommended"}
    validator._expand_caches(config)

    assert config["caches"] == RECOMMENDED_CACHES
    assert config["caches"] is not RECOMMENDED_CACHES  # Should be a copy


def test_expand_caches_no_caches_key():
    """_expand_caches doesn't fail when caches key is missing."""
    config = {"bucket_name": "test"}
    validator._expand_caches(config)

    assert "caches" not in config


def test_expand_caches_with_dict_value():
    """_expand_caches doesn't modify dict caches values."""
    original = {"text/html": 3600}
    config = {"caches": original}
    validator._expand_caches(config)

    assert config["caches"] == original


def test_validate_config_preserves_other_keys():
    """Validation preserves keys beyond targets and defaults."""
    config = {
        "version": 2,
        "targets": {"default": {}},
        "custom_key": "custom_value",
    }
    result = validator.validate_config(config)

    assert result["version"] == 2
    assert result["custom_key"] == "custom_value"
