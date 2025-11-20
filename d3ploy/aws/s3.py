"""
S3 operations.
"""

import hashlib
import mimetypes
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union

import boto3
import botocore.exceptions

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_s3.service_resource import S3ServiceResource
else:
    S3ServiceResource = object


def get_s3_resource() -> "S3ServiceResource":
    """
    Initialize and return boto3 S3 resource.

    Returns:
        boto3 S3 ServiceResource instance.
    """
    return boto3.resource("s3")


def list_buckets() -> list[str]:
    """
    List all S3 buckets accessible to the current credentials.

    Returns:
        List of bucket names.
    """
    s3 = boto3.client("s3")
    try:
        response = s3.list_buckets()
        return [bucket["Name"] for bucket in response.get("Buckets", [])]
    except botocore.exceptions.ClientError:
        return []


def test_bucket_connection(
    bucket_name: str,
    *,
    s3: Optional["S3ServiceResource"] = None,
) -> bool:
    """
    Test connection to S3 bucket.

    Args:
        bucket_name: Name of the S3 bucket.
        s3: Optional S3 resource. If None, creates a new one.

    Returns:
        True if connection successful.

    Raises:
        ClientError: If connection fails.
    """
    if s3 is None:
        s3 = get_s3_resource()

    try:
        s3.meta.client.head_bucket(Bucket=bucket_name)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "403":
            credentials = boto3.Session().get_credentials()
            access_key = credentials.access_key if credentials else "unknown"
            print(
                f'Bucket "{bucket_name}" could not be retrieved with the specified '
                f"credentials. Tried Access Key ID {access_key}",
                file=sys.stderr,
            )
            sys.exit(os.EX_NOUSER)
        else:
            raise e


def key_exists(
    s3: "S3ServiceResource",
    bucket_name: str,
    key_name: str,
) -> bool:
    """
    Check if a key exists in S3 bucket.

    Inspired by https://www.peterbe.com/plog/fastest-way-to-find-out-if-a-file-exists-in-s3

    Args:
        s3: S3 resource.
        bucket_name: Name of the S3 bucket.
        key_name: S3 key to check.

    Returns:
        True if key exists.
    """
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=key_name):
        if obj.key == key_name:
            return True
    return False


def upload_file(
    file_name: Union[str, Path],
    bucket_name: str,
    s3: "S3ServiceResource",
    bucket_path: str,
    prefix: Path,
    *,
    acl: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    charset: Optional[str] = None,
    caches: Optional[Dict[str, int]] = None,
) -> Tuple[str, int]:
    """
    Upload file to S3.

    Args:
        file_name: Local file path.
        bucket_name: Target S3 bucket.
        s3: S3 resource instance.
        bucket_path: Remote path prefix in bucket.
        prefix: Local path prefix to strip from file names.
        acl: Access control list setting.
        force: Force upload even if file unchanged.
        dry_run: Simulate upload without actually uploading.
        charset: Character set for text files.
        caches: Dictionary of MIME type patterns to cache timeouts.

    Returns:
        Tuple of (key_name, updated_count) where updated_count is 1 if uploaded, 0 if skipped.
    """
    if caches is None:
        caches = {}
    updated = 0

    if not isinstance(file_name, Path):
        file_name = Path(file_name)

    key_name = "/".join(
        [bucket_path.rstrip("/"), str(file_name.relative_to(prefix)).lstrip("/")]
    ).lstrip("/")

    if key_exists(s3, bucket_name, key_name):
        s3_obj = s3.Object(bucket_name, key_name)
    else:
        s3_obj = None

    local_md5 = hashlib.md5()
    with open(file_name, "rb") as local_file:
        for chunk in iter(lambda: local_file.read(4096), b""):
            local_md5.update(chunk)
    local_md5 = local_md5.hexdigest()

    mimetype = mimetypes.guess_type(file_name)

    if s3_obj is None or force or not s3_obj.metadata.get("d3ploy-hash") == local_md5:
        with open(file_name, "rb") as local_file:
            updated += 1
            if dry_run:
                return (key_name.lstrip("/"), updated)

            extra_args = {
                "Metadata": {"d3ploy-hash": local_md5},
            }
            if acl is not None:
                extra_args["ACL"] = acl
            if charset and mimetype[0] and mimetype[0].split("/")[0] == "text":
                extra_args["ContentType"] = f"{mimetype[0]};charset={charset}"
            elif mimetype[0]:
                extra_args["ContentType"] = mimetype[0]

            cache_timeout = None
            if mimetype[0] in caches.keys():
                cache_timeout = caches.get(mimetype[0])
            elif mimetype[0] and f"{mimetype[0].split('/')[0]}/*" in caches.keys():
                cache_timeout = caches.get(f"{mimetype[0].split('/')[0]}/*")
            if cache_timeout is not None:
                privacy = "private" if cache_timeout == 0 else "public"
                extra_args["CacheControl"] = f"max-age={cache_timeout}, {privacy}"

            s3.meta.client.upload_fileobj(
                local_file,
                bucket_name,
                key_name,
                ExtraArgs=extra_args,
            )

    return (key_name.lstrip("/"), updated)


def delete_file(
    key_name: str,
    bucket_name: str,
    s3: "S3ServiceResource",
    *,
    dry_run: bool = False,
    needs_confirmation: bool = False,
) -> int:
    """
    Delete file from S3.

    Args:
        key_name: S3 key to delete.
        bucket_name: S3 bucket name.
        s3: S3 resource instance.
        dry_run: Simulate deletion without actually deleting.
        needs_confirmation: Prompt user for confirmation before deleting.

    Returns:
        1 if file was deleted (or would be in dry-run mode), 0 otherwise.
    """
    # Check for confirmation if needed
    if needs_confirmation:
        from .. import ui

        if not ui.dialogs.confirm_delete(key_name):
            return 0

    if not dry_run:
        s3.Object(bucket_name, key_name).delete()
    return 1
