"""Integration tests for config migration scenarios."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from d3ploy.config import loader
from d3ploy.config import migration
from d3ploy.config import validator


class TestConfigMigrationIntegration:
    """Test comprehensive config migration scenarios."""

    def test_full_migration_v0_to_current(self) -> None:
        """Test complete migration from v0 (original format) to current version."""
        # Create a v0 config (original format without version)
        v0_config = {
            "defaults": {
                "local_path": "./dist",
                "bucket_path": "/",
                "acl": "public-read",
                "charset": "utf-8",
                "processes": 4,
                "gitignore": True,
                "force": False,
                "delete": False,
            },
            "environments": {
                "staging": {
                    "bucket_name": "my-staging-bucket",
                    "cloudfront_id": "ABCD1234",
                },
                "production": {
                    "bucket_name": "my-prod-bucket",
                    "cloudfront_id": "EFGH5678",
                    "acl": "private",
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(v0_config, indent=2))

            # Load and migrate the config
            loaded_config = loader.load_config(str(config_path))
            migrated_config = migration.migrate_config(loaded_config)

            # Verify the migration was successful
            assert migrated_config["version"] == migration.CURRENT_VERSION
            assert "targets" in migrated_config
            assert "environments" not in migrated_config  # Should be renamed

            # Verify targets were properly migrated
            assert "staging" in migrated_config["targets"]
            assert "production" in migrated_config["targets"]

            # Verify data integrity
            staging = migrated_config["targets"]["staging"]
            assert staging["bucket_name"] == "my-staging-bucket"
            assert staging["cloudfront_id"] == "ABCD1234"

            # Verify defaults were preserved
            assert migrated_config["defaults"]["local_path"] == "./dist"
            assert migrated_config["defaults"]["acl"] == "public-read"

    def test_migration_with_complex_config(self) -> None:
        """Test migration with complex configurations including excludes and caches."""
        complex_v1_config = {
            "version": 1,
            "defaults": {
                "local_path": "./build",
                "bucket_path": "/app",
                "acl": "public-read",
                "excludes": ["*.log", "*.tmp", ".DS_Store"],
                "processes": 8,
                "caches": {
                    "*.js": "max-age=31536000",
                    "*.css": "max-age=31536000",
                    "*.html": "no-cache",
                },
            },
            "environments": {
                "dev": {
                    "bucket_name": "dev-bucket",
                    "bucket_path": "/dev",
                    "excludes": ["*.log", "*.tmp", ".DS_Store", "debug/"],
                },
                "staging": {
                    "bucket_name": "staging-bucket",
                    "cloudfront_id": "STAGING123",
                    "caches": "recommended",
                },
                "production": {
                    "bucket_name": "prod-bucket",
                    "cloudfront_id": "PROD456",
                    "acl": "private",
                    "caches": {
                        "*.js": "max-age=63072000",  # 2 years
                        "*.css": "max-age=63072000",
                        "*.html": "no-cache, must-revalidate",
                    },
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(complex_v1_config, indent=2))

            # Load, migrate, and validate
            loaded_config = loader.load_config(str(config_path))
            migrated_config = migration.migrate_config(loaded_config)
            validator.validate_config(migrated_config)

            # Check migration was successful
            assert migrated_config["version"] == migration.CURRENT_VERSION
            assert "targets" in migrated_config

            # Verify complex data was preserved
            dev_target = migrated_config["targets"]["dev"]
            assert dev_target["bucket_path"] == "/dev"
            assert "debug/" in dev_target["excludes"]

            # Verify recommended caches were expanded
            staging_target = migrated_config["targets"]["staging"]
            assert isinstance(staging_target["caches"], dict)
            assert (
                "text/css" in staging_target["caches"]
            )  # Should contain recommended cache keys

    def test_migration_error_handling(self) -> None:
        """Test migration error handling for invalid configurations."""
        # Test with completely invalid JSON structure
        invalid_configs = [
            {"invalid": "structure"},  # Missing required keys
            {"version": 999, "targets": {}},  # Future version
            {"environments": "not_a_dict"},  # Invalid environments type
            {},  # Empty config
        ]

        for invalid_config in invalid_configs:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "d3ploy.json"
                config_path.write_text(json.dumps(invalid_config))

                try:
                    loaded_config = loader.load_config(str(config_path))
                    if (
                        loaded_config
                    ):  # If it loads, migration should handle it gracefully
                        migrated_config = migration.migrate_config(loaded_config)
                        # Should either migrate successfully or maintain original structure
                        assert isinstance(migrated_config, dict)
                except (ValueError, KeyError, TypeError):
                    # Expected for truly invalid configs
                    pass

    def test_migration_preserves_unknown_keys(self) -> None:
        """Test that migration preserves unknown/custom keys."""
        config_with_custom_keys = {
            "version": 1,
            "custom_key": "custom_value",
            "metadata": {"author": "test", "project": "test-project"},
            "defaults": {"local_path": "./dist", "acl": "public-read"},
            "environments": {
                "test": {
                    "bucket_name": "test-bucket",
                    "custom_target_key": "target_value",
                }
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(config_with_custom_keys, indent=2))

            loaded_config = loader.load_config(str(config_path))
            migrated_config = migration.migrate_config(loaded_config)

            # Custom top-level keys should be preserved
            assert migrated_config["custom_key"] == "custom_value"
            assert migrated_config["metadata"]["author"] == "test"

            # Custom target keys should be preserved
            test_target = migrated_config["targets"]["test"]
            assert test_target["custom_target_key"] == "target_value"

    def test_migration_command_generation(self) -> None:
        """Test generation of migration commands."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with default config path
            default_config = Path(temp_dir) / "d3ploy.json"
            default_config.write_text(json.dumps({"environments": {}}))

            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                command = migration.get_migration_command()
                assert "d3ploy --migrate-config" in command

            # Test with custom config path
            custom_config = Path(temp_dir) / "custom.json"
            custom_config.write_text(json.dumps({"environments": {}}))

            command = migration.get_migration_command(str(custom_config))
            assert "--migrate-config" in command
            assert str(custom_config) in command

    def test_migration_backup_and_restore(self) -> None:
        """Test migration with backup and potential restore scenarios."""
        original_config = {
            "defaults": {"local_path": "./src", "acl": "public-read"},
            "environments": {"prod": {"bucket_name": "prod-bucket"}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(original_config, indent=2))

            # Store original content for comparison
            original_content = config_path.read_text()

            # Perform migration
            loaded_config = loader.load_config(str(config_path))
            migrated_config = migration.migrate_config(loaded_config)

            # Save migrated config
            migration.save_migrated_config(migrated_config, path=str(config_path))

            # Verify the file was updated
            updated_content = config_path.read_text()
            assert updated_content != original_content

            # Verify the migrated config can be loaded again
            reloaded_config = loader.load_config(str(config_path))
            assert reloaded_config["version"] == migration.CURRENT_VERSION

    def test_multiple_config_file_locations(self) -> None:
        """Test migration works with different config file locations."""
        test_config = {
            "defaults": {"local_path": "./test"},
            "environments": {"test": {"bucket_name": "test"}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test both possible config file names
            config_files = ["d3ploy.json", ".d3ploy.json"]

            for config_name in config_files:
                config_path = Path(temp_dir) / config_name

                # Clean up any existing files
                for file in Path(temp_dir).glob("*d3ploy.json"):
                    file.unlink()

                config_path.write_text(json.dumps(test_config, indent=2))

                # Test loading and migration
                with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                    loaded_config = (
                        loader.load_config()
                    )  # Should find the file automatically
                    assert loaded_config is not None

                    migrated_config = migration.migrate_config(loaded_config)
                    assert migrated_config["version"] == migration.CURRENT_VERSION

    def test_migration_with_permission_errors(self) -> None:
        """Test migration handling when file permissions prevent writing."""
        test_config = {"environments": {"test": {"bucket_name": "test"}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "d3ploy.json"
            config_path.write_text(json.dumps(test_config))

            # Make file read-only (simulate permission error)
            config_path.chmod(0o444)

            try:
                loaded_config = loader.load_config(str(config_path))
                migrated_config = migration.migrate_config(loaded_config)

                # save_migrated_config should handle permission errors gracefully
                try:
                    migration.save_migrated_config(
                        migrated_config, path=str(config_path)
                    )
                except PermissionError:
                    # This is expected behavior - should not crash the application
                    pass

            finally:
                # Restore permissions for cleanup
                try:
                    config_path.chmod(0o644)
                except (PermissionError, FileNotFoundError):
                    pass
