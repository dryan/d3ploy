import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from d3ploy.config import load_config
from d3ploy.config import load_env_vars
from d3ploy.config import merge_config
from d3ploy.config import migrate_config
from d3ploy.config import validate_config

# Path to config fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "configs"


class TestConfigPhase3(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.temp_dir.cleanup()

    def test_merge_config(self):
        defaults = {"bucket_name": "default-bucket", "acl": "private"}
        file_config = {"bucket_name": "file-bucket"}
        env_config = {"bucket_name": "env-bucket"}
        cli_args = {"bucket_name": "cli-bucket", "force": True}

        # Test priority: CLI > Env > File > Defaults
        merged = merge_config(defaults, file_config, env_config, cli_args)
        self.assertEqual(merged["bucket_name"], "cli-bucket")
        self.assertEqual(merged["acl"], "private")
        self.assertEqual(merged["force"], True)

        # Test priority: Env > File > Defaults
        merged = merge_config(defaults, file_config, env_config, {})
        self.assertEqual(merged["bucket_name"], "env-bucket")

        # Test priority: File > Defaults
        merged = merge_config(defaults, file_config, {}, {})
        self.assertEqual(merged["bucket_name"], "file-bucket")

        # Test priority: Defaults
        merged = merge_config(defaults, {}, {}, {})
        self.assertEqual(merged["bucket_name"], "default-bucket")

    def test_load_config_d3ploy_json(self):
        config_data = {"targets": {"default": {"bucket_name": "test"}}}
        with open("d3ploy.json", "w") as f:
            json.dump(config_data, f)

        loaded = load_config()
        self.assertEqual(loaded, config_data)

    def test_load_config_dot_d3ploy_json(self):
        config_data = {"targets": {"default": {"bucket_name": "test"}}}
        with open(".d3ploy.json", "w") as f:
            json.dump(config_data, f)

        loaded = load_config()
        self.assertEqual(loaded, config_data)

    def test_load_config_explicit_path(self):
        config_data = {"targets": {"default": {"bucket_name": "test"}}}
        with open("custom.json", "w") as f:
            json.dump(config_data, f)

        loaded = load_config("custom.json")
        self.assertEqual(loaded, config_data)

    def test_validate_config_valid(self):
        config_data = {"targets": {"default": {}}}
        validated = validate_config(config_data)
        self.assertEqual(validated, config_data)

    def test_validate_config_invalid_type(self):
        with self.assertRaises(ValueError):
            validate_config([])

    def test_validate_config_missing_environments(self):
        with self.assertRaises(ValueError):
            validate_config({"defaults": {}})

    def test_migrate_config_v0_to_v2(self):
        v0_config = {"environments": {}}
        migrated = migrate_config(v0_config)
        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["targets"], {})
        self.assertNotIn("environments", migrated)

    def test_migrate_config_v1_to_v2(self):
        v1_config = {"version": 1, "environments": {"default": {}}}
        migrated = migrate_config(v1_config)
        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["targets"], {"default": {}})
        self.assertNotIn("environments", migrated)

    def test_migrate_config_v2_no_change(self):
        v2_config = {"version": 2, "targets": {"default": {}}}
        migrated = migrate_config(v2_config)
        self.assertEqual(migrated, v2_config)

    def test_validate_config_recommended_caches(self):
        config_data = {"targets": {"default": {"caches": "recommended"}}}
        validated = validate_config(config_data)
        self.assertIsInstance(validated["targets"]["default"]["caches"], dict)
        self.assertEqual(validated["targets"]["default"]["caches"]["text/html"], 0)

    def test_load_env_vars(self):
        os.environ["D3PLOY_BUCKET_NAME"] = "env-bucket"
        os.environ["D3PLOY_PROCESSES"] = "20"

        env_vars = load_env_vars()
        self.assertEqual(env_vars["bucket_name"], "env-bucket")
        self.assertEqual(env_vars["processes"], 20)

        del os.environ["D3PLOY_BUCKET_NAME"]
        del os.environ["D3PLOY_PROCESSES"]

    def test_migrate_v0_fixture(self):
        """Test migration using v0 fixture file."""
        v0_config = json.loads((FIXTURES_DIR / "v0-config.json").read_text())
        migrated = migrate_config(v0_config)

        # Should be upgraded to v2
        self.assertEqual(migrated["version"], 2)
        # Should have targets, not environments
        self.assertIn("targets", migrated)
        self.assertNotIn("environments", migrated)
        # Should preserve all target configs
        self.assertIn("default", migrated["targets"])
        self.assertIn("staging", migrated["targets"])
        # Should preserve defaults
        self.assertIn("defaults", migrated)
        self.assertIn("caches", migrated["defaults"])

    def test_migrate_v1_fixture(self):
        """Test migration using v1 fixture file."""
        v1_config = json.loads((FIXTURES_DIR / "v1-config.json").read_text())
        migrated = migrate_config(v1_config)

        # Should be upgraded to v2
        self.assertEqual(migrated["version"], 2)
        # Should have targets, not environments
        self.assertIn("targets", migrated)
        self.assertNotIn("environments", migrated)
        # Should preserve cloudfront_id
        self.assertEqual(
            migrated["targets"]["staging"]["cloudfront_id"],
            "E1234567890ABC",
        )

    def test_v2_fixture_current(self):
        """Test that v2 fixture is already current version."""
        v2_config = json.loads((FIXTURES_DIR / "v2-config.json").read_text())
        migrated = migrate_config(v2_config)

        # Should be unchanged
        self.assertEqual(migrated, v2_config)
        self.assertEqual(migrated["version"], 2)


if __name__ == "__main__":
    unittest.main()
