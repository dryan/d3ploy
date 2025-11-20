"""
Tests for d3ploy.aws.s3 upload functionality (UploadFileTestCase conversion).
"""

import uuid
from unittest.mock import patch

import pytest

from d3ploy.aws import s3

# Valid ACLs for S3
VALID_ACLS = ["private", "public-read", "public-read-write", "authenticated-read"]

# Character sets to test
CHARSETS = [None, "UTF-8", "ISO-8859-1", "Windows-1251"]

# MIME types to test
TEST_MIMETYPES = [
    ("css/sample.css", "text/css"),
    ("fonts/open-sans.eot", "application/vnd.ms-fontobject"),
    ("fonts/open-sans.svg", "image/svg+xml"),
    ("fonts/open-sans.ttf", "font/ttf"),
    ("fonts/open-sans.woff", "font/woff"),
    ("fonts/open-sans.woff2", "font/woff2"),
    ("img/32d08f4a5eb10332506ebedbb9bc7257.jpg", "image/jpeg"),
    ("img/6c853ed9dacd5716bc54eb59cec30889.png", "image/png"),
    ("img/6d939393058de0579fca1bbf10ecff25.gif", "image/gif"),
    ("img/http.svg", "image/svg+xml"),
    ("html/index.html", "text/html"),
    ("js/sample.js", "text/javascript"),
    ("js/sample.mjs", "text/javascript"),
    ("sample.json", "application/json"),
    ("sample.xml", "application/xml"),
]


@pytest.fixture
def prefix_path(files_dir):
    """Return the test files prefix path."""
    return files_dir


# Tests for upload_file


def test_upload_file_bucket_path(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file returns the correct path for different prefixes."""
    test_file = files_dir / "css" / "sample.css"

    for prefix in ["test", "testing"]:
        result = s3.upload_file(
            test_file,
            test_bucket_name,
            s3_resource,
            prefix,
            prefix_path,
        )

        assert result[0] == f"{prefix}/css/sample.css"
        assert result[1] == 1  # File was uploaded


def test_upload_file_with_path_as_str(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file accepts path as string."""
    test_file = str(files_dir / "css" / "sample.css")

    result = s3.upload_file(
        test_file,
        test_bucket_name,
        s3_resource,
        "test",
        prefix_path,
    )

    assert result[0] == "test/css/sample.css"
    assert result[1] == 1  # File was uploaded


def test_upload_file_acls(
    clean_s3_bucket,
    s3_resource,
    files_dir,
    prefix_path,
    test_bucket_name,
    acl_grants,
):
    """upload_file sets the correct ACL grants."""
    test_file = files_dir / "css" / "sample.css"

    for acl in VALID_ACLS:
        result = s3.upload_file(
            test_file,
            test_bucket_name,
            s3_resource,
            f"test-acl-{acl}",
            prefix_path,
            acl=acl,
        )

        # Verify ACL was set correctly
        object_acl = s3_resource.ObjectAcl(test_bucket_name, result[0])
        grants = []
        for grant in object_acl.grants:
            if grant.get("Grantee", {}).get("Type") == "CanonicalUser":
                continue  # skip the individual user permissions
            grants.append(grant)

        assert grants == acl_grants.get(acl), f"ACL {acl} grants should match"


def test_upload_file_force_update(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file force=True overwrites existing file."""
    test_file = files_dir / "css" / "sample.css"

    # Upload once
    s3.upload_file(
        test_file,
        test_bucket_name,
        s3_resource,
        "test-force-upload",
        prefix_path,
    )

    # Upload again with force=True
    result = s3.upload_file(
        test_file,
        test_bucket_name,
        s3_resource,
        "test-force-upload",
        prefix_path,
        force=True,
    )

    assert result[1] > 0, "Force upload should update the file"


def test_upload_file_md5_hashing(
    clean_s3_bucket,
    s3_resource,
    test_file_path,
    prefix_path,
    test_bucket_name,
):
    """upload_file uses MD5 hashing to detect changes."""
    # Create initial test file
    test_file_path.parent.mkdir(parents=True, exist_ok=True)
    test_file_path.write_text(f"{uuid.uuid4().hex}\n")

    # First upload
    result_1 = s3.upload_file(
        test_file_path,
        test_bucket_name,
        s3_resource,
        "test-md5-hashing",
        prefix_path,
    )

    assert s3.key_exists(s3_resource, test_bucket_name, result_1[0])
    s3_obj_1 = s3_resource.Object(test_bucket_name, result_1[0])
    s3_hash_1 = s3_obj_1.metadata.get("d3ploy-hash")
    assert result_1[1] == 1, "First upload should update"

    # Second upload without changes
    result_2 = s3.upload_file(
        test_file_path,
        test_bucket_name,
        s3_resource,
        "test-md5-hashing",
        prefix_path,
    )

    assert s3.key_exists(s3_resource, test_bucket_name, result_2[0])
    s3_obj_2 = s3_resource.Object(test_bucket_name, result_2[0])
    s3_hash_2 = s3_obj_2.metadata.get("d3ploy-hash")
    assert result_2[1] == 0, "Unchanged file should not upload"
    assert s3_hash_1 == s3_hash_2, "Hashes should match"

    # Third upload with changes
    test_file_path.write_text(f"{uuid.uuid4().hex}\n")
    result_3 = s3.upload_file(
        test_file_path,
        test_bucket_name,
        s3_resource,
        "test-md5-hashing",
        prefix_path,
    )

    s3_obj_3 = s3_resource.Object(test_bucket_name, result_3[0])
    s3_hash_3 = s3_obj_3.metadata.get("d3ploy-hash")
    assert result_3[1] == 1, "Changed file should upload"
    assert s3_hash_1 != s3_hash_3, "Hashes should differ"


def test_upload_file_dry_run(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file dry_run=True does not upload the file."""
    test_file = files_dir / "css" / "sample.css"

    result = s3.upload_file(
        test_file,
        test_bucket_name,
        s3_resource,
        "test-dry-run",
        prefix_path,
        dry_run=True,
    )

    assert result[1] == 1  # Would have uploaded
    assert not s3.key_exists(s3_resource, test_bucket_name, result[0]), (
        "File should not exist in S3"
    )


def test_upload_file_charset(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file sets charset for text files."""
    test_file = files_dir / "html" / "index.html"

    for charset in CHARSETS:
        result = s3.upload_file(
            test_file,
            test_bucket_name,
            s3_resource,
            f"test-charset-{charset}",
            prefix_path,
            charset=charset,
        )

        s3_obj = s3_resource.Object(test_bucket_name, result[0])
        if charset:
            assert s3_obj.content_type == f"text/html;charset={charset}"
        else:
            assert s3_obj.content_type == "text/html"


def test_upload_file_caches(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file sets proper cache-control headers."""
    test_file = files_dir / "css" / "sample.css"

    for expiration in [0, 86400, 86400 * 30, 86400 * 365]:
        result = s3.upload_file(
            test_file,
            test_bucket_name,
            s3_resource,
            f"test-cache-{expiration:d}",
            prefix_path,
            caches={"text/css": expiration},
        )

        s3_obj = s3_resource.Object(test_bucket_name, result[0])
        if expiration == 0:
            assert s3_obj.cache_control == f"max-age={expiration}, private", (
                f"Cache control should be private for max-age={expiration}"
            )
        else:
            assert s3_obj.cache_control == f"max-age={expiration}, public", (
                f"Cache control should be public for max-age={expiration}"
            )


def test_upload_file_caches_wildcard(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file sets proper cache-control headers with wildcard patterns."""
    test_file = files_dir / "css" / "sample.css"

    # Test wildcard pattern like "text/*" matching "text/css"
    result = s3.upload_file(
        test_file,
        test_bucket_name,
        s3_resource,
        "test-cache-wildcard",
        prefix_path,
        caches={"text/*": 3600},
    )

    s3_obj = s3_resource.Object(test_bucket_name, result[0])
    assert s3_obj.cache_control == "max-age=3600, public", (
        "Wildcard cache pattern should match"
    )


def test_upload_file_mimetypes(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file sets the correct MIME type for various files."""
    for file_path, expected_mimetype in TEST_MIMETYPES:
        test_file = files_dir / file_path

        result = s3.upload_file(
            test_file,
            test_bucket_name,
            s3_resource,
            "test-mimetypes",
            prefix_path,
        )

        assert s3.key_exists(s3_resource, test_bucket_name, result[0])
        s3_obj = s3_resource.Object(test_bucket_name, result[0])
        assert s3_obj.content_type == expected_mimetype, (
            f"MIME type for {file_path} should be {expected_mimetype}"
        )


def test_upload_file_with_killswitch_flipped(
    clean_s3_bucket, s3_resource, files_dir, prefix_path, test_bucket_name
):
    """upload_file raises UserCancelled when signal received during operation."""
    from d3ploy.core.signals import UserCancelled
    from d3ploy.sync import operations

    test_file = files_dir / "css" / "sample.css"

    # Simulate signal being triggered during file read
    def raise_cancelled(*args, **kwargs):
        operations.killswitch.set()
        raise UserCancelled("Operation cancelled")

    with patch("builtins.open", side_effect=raise_cancelled):
        with pytest.raises(UserCancelled):
            s3.upload_file(
                test_file,
                test_bucket_name,
                s3_resource,
                "test-upload-killswitch",
                prefix_path,
            )
