"""
Pytest configuration and shared fixtures for d3ploy tests.

Provides common fixtures for S3 buckets, test files, mocks, and other
test utilities used across multiple test modules.
"""

import os
import pathlib
import uuid
from collections.abc import Generator
from typing import Any

import boto3
import pytest

# Test constants
TEST_BUCKET = os.getenv("D3PLOY_TEST_BUCKET", "d3ploy-tests")
TEST_CLOUDFRONT_DISTRIBUTION = os.getenv(
    "D3PLOY_TEST_CLOUDFRONT_DISTRIBUTION",
    "ECVGU5V5GT5GO",
)

# Test file paths
TESTS_DIR = pathlib.Path(__file__).parent
FILES_DIR = TESTS_DIR / "files"
FIXTURES_DIR = TESTS_DIR / "fixtures"

TEST_FILES = [
    "tests/files/.d3ploy.json",
    "tests/files/.empty-config.json",
    "tests/files/.test-d3ploy",
    "tests/files/css/sample.css",
    "tests/files/dont.ignoreme",
    "tests/files/fonts/open-sans.eot",
    "tests/files/fonts/open-sans.svg",
    "tests/files/fonts/open-sans.ttf",
    "tests/files/fonts/open-sans.woff",
    "tests/files/fonts/open-sans.woff2",
    "tests/files/html/index.html",
    "tests/files/img/32d08f4a5eb10332506ebedbb9bc7257.jpg",
    "tests/files/img/40bb78b1ac031125a6d8466b374962a8.jpg",
    "tests/files/img/6c853ed9dacd5716bc54eb59cec30889.png",
    "tests/files/img/6d939393058de0579fca1bbf10ecff25.gif",
    "tests/files/img/9540743374e1fdb273b6a6ca625eb7a3.png",
    "tests/files/img/c-m1-4bdd87fd0324f0a3d84d6905d17e1731.png",
    "tests/files/img/d22db5be7594c17a18a047ca9264ea0a.jpg",
    "tests/files/img/e6aa0c45a13dd7fc94f7b5451bd89bf4.gif",
    "tests/files/img/f617c7af7f36296a37ddb419b828099c.gif",
    "tests/files/img/http.svg",
    "tests/files/js/sample.js",
    "tests/files/js/sample.mjs",
    "tests/files/sample.json",
    "tests/files/sample.xml",
]

TEST_FILES_WITH_IGNORED = TEST_FILES + [
    "tests/files/js/ignore.js",
    "tests/files/please.ignoreme",
    "tests/files/test.ignore",
]

# ACL grants for testing S3 permissions
ACL_GRANTS = {
    "private": [],
    "public-read": [
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    ],
    "public-read-write": [
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        },
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "WRITE",
        },
    ],
    "authenticated-read": [
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
            },
            "Permission": "READ",
        }
    ],
}


@pytest.fixture(scope="session")
def tests_dir() -> pathlib.Path:
    """Return the tests directory path."""
    return TESTS_DIR


@pytest.fixture(scope="session")
def files_dir() -> pathlib.Path:
    """Return the test files directory path."""
    return FILES_DIR


@pytest.fixture(scope="session")
def fixtures_dir() -> pathlib.Path:
    """Return the fixtures directory path."""
    return FIXTURES_DIR


@pytest.fixture
def clean_ds_store():
    """Remove .DS_Store files from test directories (macOS)."""
    for ds_store in TESTS_DIR.rglob(".DS_Store"):
        ds_store.unlink()
    yield
    for ds_store in TESTS_DIR.rglob(".DS_Store"):
        ds_store.unlink()


@pytest.fixture(scope="session")
def s3_resource():
    """Create an S3 resource for testing."""
    return boto3.resource("s3")


@pytest.fixture(scope="session")
def s3_bucket(s3_resource):
    """Get the S3 test bucket."""
    bucket = s3_resource.Bucket(TEST_BUCKET)
    return bucket


@pytest.fixture
def clean_s3_bucket(s3_bucket):
    """Clean the S3 bucket before and after each test."""
    # Clean before test
    s3_bucket.objects.all().delete()
    yield s3_bucket
    # Clean after test
    s3_bucket.objects.all().delete()


@pytest.fixture
def test_file_path(files_dir) -> Generator[pathlib.Path, None, None]:
    """Create a unique test file path."""
    test_file = files_dir / "txt" / f"test-{uuid.uuid4().hex}.txt"
    yield test_file
    # Cleanup
    if test_file.exists():
        test_file.unlink()


@pytest.fixture
def create_test_file(test_file_path):
    """Fixture that creates a test file with random content."""

    def _create():
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text(f"{uuid.uuid4().hex}\n")
        return test_file_path

    yield _create
    # Cleanup
    if test_file_path.exists():
        test_file_path.unlink()


@pytest.fixture
def mock_s3_object_exists(mocker):
    """Mock the s3_object_exists function."""
    return mocker.patch("d3ploy.aws.s3.key_exists")


@pytest.fixture
def acl_grants() -> dict[str, list[dict[str, Any]]]:
    """Return ACL grant definitions for testing."""
    return ACL_GRANTS


@pytest.fixture
def test_bucket_name() -> str:
    """Return the test bucket name."""
    return TEST_BUCKET


@pytest.fixture
def test_cloudfront_id() -> str:
    """Return the test CloudFront distribution ID."""
    return TEST_CLOUDFRONT_DISTRIBUTION


@pytest.fixture
def sample_config() -> dict:
    """Return a sample d3ploy configuration."""
    return {
        "version": 2,
        "targets": {
            "default": {
                "bucket_name": "test-bucket",
                "local_path": ".",
                "bucket_path": "/",
            },
            "staging": {
                "bucket_name": "test-bucket",
                "local_path": ".",
                "bucket_path": "/staging/",
            },
        },
        "defaults": {
            "acl": "public-read",
            "exclude": [".gitignore", ".gitkeep"],
        },
    }


@pytest.fixture
def temp_config_file(tmp_path, sample_config):
    """Create a temporary config file."""
    config_file = tmp_path / "d3ploy.json"
    import json

    config_file.write_text(json.dumps(sample_config, indent=2))
    return config_file
