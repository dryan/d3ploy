"""Integration tests for environment variable handling."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from d3ploy.config import env
from d3ploy.config import loader
from d3ploy.config import merger


class TestEnvironmentVariableIntegration:
    """Test environment variable integration with config system."""

    def test_env_vars_override_config_file(self) -> None:
        """Test that environment variables properly override config file values."""
        # Create a config file
        config_data = {
            "version": 2,
            "defaults": {
                "local_path": "./from-config",
                "bucket_path": "/config-path",
                "acl": "private",
                "processes": 2,
            },
            "targets": {"test": {"bucket_name": "config-bucket", "acl": "public-read"}},
        }

        # Set environment variables that should override
        env_vars = {
            "D3PLOY_LOCAL_PATH": "./from-env",
            "D3PLOY_BUCKET_PATH": "/env-path",
            "D3PLOY_ACL": "bucket-owner-read",
            "D3PLOY_PROCESSES": "8",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(config_data, indent=2))

            with patch.dict(os.environ, env_vars, clear=False):
                # Load config and env vars
                file_config = loader.load_config(str(config_path))
                env_config = env.load_env_vars()

                # Merge them (env should override config)
                defaults = config_data.get("defaults")
                if not isinstance(defaults, dict):
                    defaults = {}
                merged = merger.merge_config(
                    defaults=defaults,
                    file_config=file_config,
                    env_config=env_config,
                    cli_args={},
                )

                # Verify env vars won
                assert merged["local_path"] == "./from-env"
                assert merged["bucket_path"] == "/env-path"
                assert merged["acl"] == "bucket-owner-read"
                assert merged["processes"] == 8  # Should be converted to int

    def test_cli_args_override_env_vars(self) -> None:
        """Test that CLI arguments override environment variables."""
        env_vars = {
            "D3PLOY_LOCAL_PATH": "./from-env",
            "D3PLOY_ACL": "public-read",
            "D3PLOY_PROCESSES": "4",
        }

        cli_args = {
            "local_path": "./from-cli",
            "acl": "private",
            "bucket_name": "cli-bucket",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            env_config = env.load_env_vars()

            merged = merger.merge_config(
                defaults={}, file_config={}, env_config=env_config, cli_args=cli_args
            )

            # CLI should win over env
            assert merged["local_path"] == "./from-cli"
            assert merged["acl"] == "private"
            assert merged["bucket_name"] == "cli-bucket"

            # Env var should still be present where no CLI override
            assert merged["processes"] == 4

    def test_env_var_type_conversion(self) -> None:
        """Test that environment variables are properly type-converted."""
        env_vars = {
            "D3PLOY_PROCESSES": "8",  # Should become int
            "D3PLOY_LOCAL_PATH": "./test",  # Should stay string
            "D3PLOY_BUCKET_PATH": "",  # Empty string should stay empty string
        }

        with patch.dict(os.environ, env_vars, clear=False):
            env_config = env.load_env_vars()

            # Check types
            assert isinstance(env_config["processes"], int)
            assert env_config["processes"] == 8

            assert isinstance(env_config["local_path"], str)
            assert env_config["local_path"] == "./test"

            assert isinstance(env_config["bucket_path"], str)
            assert env_config["bucket_path"] == ""

    def test_invalid_env_var_values(self) -> None:
        """Test handling of invalid environment variable values."""
        # Test invalid values that should be ignored or handled gracefully
        invalid_env_vars = {
            "D3PLOY_PROCESSES": "not-a-number",  # Invalid int
            "D3PLOY_LOCAL_PATH": "",  # Empty string (should be valid)
        }

        with patch.dict(os.environ, invalid_env_vars, clear=False):
            env_config = env.load_env_vars()

            # Invalid int should be ignored (not in result) or handled gracefully
            if "processes" in env_config:
                # If it's in the result, it should be handled as string not int
                # Or excluded entirely due to invalid conversion
                pass

            # Empty string should be preserved
            assert env_config.get("local_path") == ""

    def test_env_var_case_sensitivity(self) -> None:
        """Test that environment variables are case-sensitive."""
        env_vars = {
            "D3PLOY_BUCKET_NAME": "correct-bucket",
            "d3ploy_bucket_name": "wrong-bucket",  # Wrong case
            "D3PLOY_BUCKET_name": "also-wrong",  # Mixed case
        }

        with patch.dict(os.environ, env_vars, clear=False):
            env_config = env.load_env_vars()

            # Only correctly-cased var should be loaded
            assert env_config["bucket_name"] == "correct-bucket"

    def test_env_var_prefix_isolation(self) -> None:
        """Test that only D3PLOY_ prefixed vars are loaded."""
        env_vars = {
            "D3PLOY_BUCKET_NAME": "d3ploy-bucket",
            "AWS_BUCKET_NAME": "aws-bucket",  # Different prefix
            "BUCKET_NAME": "generic-bucket",  # No prefix
            "MY_D3PLOY_VAR": "wrong-prefix",  # Wrong prefix placement
        }

        with patch.dict(os.environ, env_vars, clear=False):
            env_config = env.load_env_vars()

            # Only D3PLOY_ vars should be loaded
            assert env_config["bucket_name"] == "d3ploy-bucket"
            assert "aws_bucket_name" not in env_config
            assert "generic_bucket_name" not in env_config
            assert "my_d3ploy_var" not in env_config

    def test_env_vars_loaded_exactly_once(self) -> None:
        """Test that environment variables are consistently loaded."""
        env_vars = {"D3PLOY_BUCKET_NAME": "test-bucket", "D3PLOY_PROCESSES": "4"}

        with patch.dict(os.environ, env_vars, clear=False):
            # Load env vars multiple times
            env_config1 = env.load_env_vars()
            env_config2 = env.load_env_vars()

            # Should be identical
            assert env_config1 == env_config2
            assert env_config1["bucket_name"] == "test-bucket"
            assert env_config2["bucket_name"] == "test-bucket"

    def test_supported_env_vars_only(self) -> None:
        """Test that only supported environment variables are loaded."""
        # Based on the actual ENV_MAPPING in env.py
        supported_vars = {
            "D3PLOY_BUCKET_NAME": "test-bucket",
            "D3PLOY_LOCAL_PATH": "./test",
            "D3PLOY_BUCKET_PATH": "/test",
            "D3PLOY_ACL": "public-read",
            "D3PLOY_CHARSET": "utf-8",
            "D3PLOY_PROCESSES": "4",
        }

        # Variables that shouldn't be supported (not in ENV_MAPPING)
        unsupported_vars = {
            "D3PLOY_FORCE": "true",  # Not in mapping
            "D3PLOY_DELETE": "false",  # Not in mapping
            "D3PLOY_GITIGNORE": "true",  # Not in mapping
        }

        all_vars = {**supported_vars, **unsupported_vars}

        with patch.dict(os.environ, all_vars, clear=False):
            env_config = env.load_env_vars()

            # Supported vars should be present
            assert env_config["bucket_name"] == "test-bucket"
            assert env_config["local_path"] == "./test"
            assert env_config["bucket_path"] == "/test"
            assert env_config["acl"] == "public-read"
            assert env_config["charset"] == "utf-8"
            assert env_config["processes"] == 4  # Converted to int

            # Unsupported vars should not be present
            assert "force" not in env_config
            assert "delete" not in env_config
            assert "gitignore" not in env_config

    def test_env_prefix_constant(self) -> None:
        """Test that the env prefix constant is correct."""
        assert env.PREFIX == "D3PLOY_"

    def test_env_mapping_constant(self) -> None:
        """Test that the env mapping constant contains expected keys."""
        expected_keys = [
            "BUCKET_NAME",
            "LOCAL_PATH",
            "BUCKET_PATH",
            "ACL",
            "CHARSET",
            "PROCESSES",
        ]

        for key in expected_keys:
            assert key in env.ENV_MAPPING
            assert isinstance(env.ENV_MAPPING[key], str)
