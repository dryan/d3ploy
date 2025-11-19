"""
File synchronization operations and coordination.
"""

import os
import pathlib
import sys
import threading
from concurrent import futures
from pathlib import Path
from typing import Collection
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from .. import aws
from .. import ui
from . import discovery

# Global killswitch for graceful shutdown
killswitch = threading.Event()


def get_progress_bar(
    *args,
    quiet: bool = False,
    **kwargs,
) -> ui.ProgressDisplay:
    """
    Create a progress bar with standard settings.

    Args:
        *args: Positional arguments (total, description).
        quiet: Whether to disable progress display.
        **kwargs: Keyword arguments.

    Returns:
        Configured ProgressDisplay.
    """
    # Extract positional args (if any)
    total = args[0] if len(args) > 0 else kwargs.pop("total", None)
    description = kwargs.pop("desc", kwargs.pop("description", ""))

    kwargs.setdefault("unit", "files")
    colour = kwargs.pop("colour", "green")

    return ui.ProgressDisplay(
        total=total,
        description=description,
        disable=quiet,
        colour=colour,
        **kwargs,
    )


def alert(
    text: str,
    *,
    error_code: Optional[int] = None,
    color: Optional[str] = None,
    quiet: bool = False,
):
    """
    Display a message and optionally exit.

    Args:
        text: Message to display.
        error_code: Exit code (exits if not None).
        color: Deprecated - maintained for backward compatibility.
        quiet: Suppress non-error output.
    """
    # Determine level from error_code
    if error_code is not None and error_code != os.EX_OK:
        level = "error"
    elif error_code == os.EX_OK:
        level = "success"
    else:
        level = "info"

    ui.output.display_message(text, level=level, quiet=quiet)

    if error_code is not None:
        sys.exit(error_code)


def get_confirmation(message: str) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Confirmation prompt.

    Returns:
        True if user confirms.
    """
    confirm = input(f"{message} [yN]: ")
    return confirm.lower() in ["y", "yes"]


def upload_batch(
    files: List[Path],
    bucket_name: str,
    s3_resource,
    bucket_path: str,
    prefix: Path,
    *,
    acl: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    charset: Optional[str] = None,
    caches: Optional[Dict[str, int]] = None,
    processes: int = 1,
    env: str = "",
    quiet: bool = False,
) -> Tuple[List[Tuple[str, int]], int]:
    """
    Upload batch of files using thread pool.

    Args:
        files: Files to upload.
        bucket_name: Target S3 bucket.
        s3_resource: S3 resource instance.
        bucket_path: Remote path prefix.
        prefix: Local path prefix to strip.
        acl: Access control list setting.
        force: Force upload even if unchanged.
        dry_run: Simulate without uploading.
        charset: Character set for text files.
        caches: Cache control settings.
        processes: Number of concurrent processes.
        env: Environment name for display.
        quiet: Suppress output.

    Returns:
        Tuple of (list of (key_name, updated_count), total_updated_count).
    """
    if caches is None:
        caches = {}

    key_names = []
    with get_progress_bar(
        desc=f"[green]Updating {env}[/green]",
        total=len(files),
        quiet=quiet,
    ) as bar:
        with futures.ThreadPoolExecutor(max_workers=processes) as executor:
            jobs = []
            for fn in files:
                job = executor.submit(
                    aws.s3.upload_file,
                    fn,
                    bucket_name,
                    s3_resource,
                    bucket_path,
                    prefix,
                    acl=acl,
                    force=force,
                    dry_run=dry_run,
                    charset=charset,
                    caches=caches,
                )
                jobs.append(job)

            for job in futures.as_completed(jobs):
                if killswitch.is_set():
                    break
                result = job.result()
                key_names.append(result)
                bar.update()

            executor.shutdown(wait=True)

    updated = sum([i[1] for i in key_names])
    return key_names, updated


def delete_orphans(
    bucket_name: str,
    s3_resource,
    bucket_path: str,
    local_files: List[str],
    *,
    needs_confirmation: bool = False,
    dry_run: bool = False,
    processes: int = 1,
    env: str = "",
    quiet: bool = False,
) -> int:
    """
    Delete files from S3 that no longer exist locally.

    Args:
        bucket_name: S3 bucket name.
        s3_resource: S3 resource instance.
        bucket_path: Remote path prefix.
        local_files: List of local file keys that should exist.
        needs_confirmation: Prompt before each deletion.
        dry_run: Simulate without deleting.
        processes: Number of concurrent processes.
        env: Environment name for display.
        quiet: Suppress output.

    Returns:
        Number of files deleted.
    """
    bucket = s3_resource.Bucket(bucket_name)
    to_remove = [
        key.key
        for key in bucket.objects.filter(Prefix=bucket_path.lstrip("/"))
        if key.key.lstrip("/") not in local_files
    ]

    if not to_remove:
        return 0

    deleted = 0
    with get_progress_bar(
        desc=f"[red]Cleaning {env}[/red]",
        total=len(to_remove),
        colour="red",
        quiet=quiet,
    ) as bar:
        with futures.ThreadPoolExecutor(max_workers=processes) as executor:
            jobs = []
            for kn in to_remove:
                if needs_confirmation:
                    confirmed = get_confirmation(
                        f"\nRemove {bucket_name}/{kn.lstrip('/')}"
                    )
                    if not confirmed:
                        alert(
                            f"\nSkipping removal of {bucket_name}/{kn.lstrip('/')}",
                            quiet=quiet,
                        )
                        bar.update()
                        continue

                job = executor.submit(
                    aws.s3.delete_file,
                    kn,
                    bucket_name,
                    s3_resource,
                    dry_run=dry_run,
                )
                jobs.append(job)

            for job in futures.as_completed(jobs):
                if killswitch.is_set():
                    break
                deleted += job.result()
                bar.update()

            executor.shutdown(wait=True)

    return deleted


def sync_target(
    target: str,
    *,
    bucket_name: Optional[str] = None,
    local_path: Union[str, Path, None] = ".",
    bucket_path: Optional[str] = "/",
    excludes: Collection[str] = [],
    acl: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    charset: Optional[str] = None,
    gitignore: bool = False,
    processes: int = 1,
    delete: bool = False,
    confirm: bool = False,
    cloudfront_id: Union[List[str], str, None] = None,
    caches: Optional[Dict[str, int]] = None,
    quiet: bool = False,
    using_config: bool = True,
) -> Dict[str, int]:
    """
    Coordinate sync operation for a target.

    Args:
        target: Target name.
        bucket_name: S3 bucket name.
        local_path: Local directory to sync from.
        bucket_path: Remote directory to sync to.
        excludes: List of exclude patterns.
        acl: Access control list setting.
        force: Force upload all files.
        dry_run: Simulate without making changes.
        charset: Character set for text files.
        gitignore: Respect .gitignore rules.
        processes: Number of concurrent processes.
        delete: Delete orphaned files.
        confirm: Prompt before deletions.
        cloudfront_id: CloudFront distribution ID(s).
        caches: Cache control settings.
        quiet: Suppress output.
        using_config: Whether using a config file target.

    Returns:
        Dictionary with counts of uploaded, deleted, invalidated files.
    """
    if using_config:
        alert(f'Using settings for "{target}" target', quiet=quiet)
    else:
        alert(f'Syncing to "{bucket_name}"', quiet=quiet)

    if cloudfront_id is None:
        cloudfront_id = []

    if caches is None:
        caches = {}

    if not isinstance(local_path, pathlib.Path):
        local_path = pathlib.Path(local_path)

    if not bucket_name:
        alert(
            f'A bucket to upload to was not specified for "{target}" target',
            error_code=os.EX_NOINPUT,
            quiet=quiet,
        )

    # Type checker: bucket_name is guaranteed non-None after the check above
    # (alert with error_code calls sys.exit, so we won't reach here if bucket_name is None)
    assert bucket_name is not None
    assert bucket_path is not None

    s3_resource = aws.s3.get_s3_resource()

    # Test bucket connection
    aws.s3.test_bucket_connection(bucket_name, s3=s3_resource)

    # Discover files to sync
    files = discovery.discover_files(local_path, excludes=excludes, gitignore=gitignore)

    # Upload files
    key_names, updated = upload_batch(
        files,
        bucket_name,
        s3_resource,
        bucket_path,
        local_path,
        acl=acl,
        force=force,
        dry_run=dry_run,
        charset=charset,
        caches=caches,
        processes=processes,
        env=target,
        quiet=quiet,
    )

    # Extract just the key names for deletion comparison
    key_names_list = [i[0] for i in key_names if i[0]]

    # Delete orphaned files if requested
    deleted = 0
    if delete and not killswitch.is_set():
        deleted = delete_orphans(
            bucket_name,
            s3_resource,
            bucket_path,
            key_names_list,
            needs_confirmation=confirm,
            dry_run=dry_run,
            processes=processes,
            env=target,
            quiet=quiet,
        )

    # Display results
    verb = "would be" if dry_run else "were"
    outcome = {
        "uploaded": updated,
        "deleted": deleted,
        "invalidated": 0,
    }

    alert("", quiet=quiet)
    ui.output.display_message(
        (
            f"{updated:d} file{'' if updated == 1 else 's'} "
            f"{'was' if verb == 'were' and updated == 1 else verb} updated"
        ),
        level="success",
        quiet=quiet,
    )

    if delete:
        ui.output.display_message(
            (
                f"{deleted:d} file{'' if deleted == 1 else 's'} "
                f"{'was' if verb == 'were' and deleted == 1 else verb} removed"
            ),
            level="warning",
            quiet=quiet,
        )

    # Invalidate CloudFront if needed
    if cloudfront_id and (updated or deleted):
        invalidations = aws.cloudfront.invalidate_distributions(
            cloudfront_id,
            dry_run=dry_run,
        )
        outcome["invalidated"] = len(invalidations)

        if not dry_run:
            for cf_id in (
                cloudfront_id if isinstance(cloudfront_id, list) else [cloudfront_id]
            ):
                ui.output.display_message(
                    f"CloudFront distribution {cf_id} invalidation requested",
                    level="success",
                    quiet=quiet,
                )
        else:
            for cf_id in (
                cloudfront_id if isinstance(cloudfront_id, list) else [cloudfront_id]
            ):
                ui.output.display_message(
                    f"CloudFront distribution {cf_id} invalidation would be requested",
                    level="success",
                    quiet=quiet,
                )
    elif cloudfront_id:
        outcome["invalidated"] = 0
        alert("CloudFront invalidation skipped because no files changed", quiet=quiet)

    return outcome
