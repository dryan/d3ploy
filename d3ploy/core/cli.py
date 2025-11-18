"""
CLI argument parsing and main entry point.
"""

import argparse
import json
import os
import pathlib
from typing import Union

from .. import __version__
from ..compat import colorama
from ..sync import operations
from . import signals
from . import updates

VALID_ACLS = [
    "private",
    "public-read",
    "public-read-write",
    "authenticated-read",
]


def processes_int(x: Union[str, int, float]) -> int:
    """
    Validate and convert processes argument.

    Args:
        x: Value to convert.

    Returns:
        Integer between 1 and 50.

    Raises:
        argparse.ArgumentTypeError: If value out of range.
    """
    x = int(x)
    if x < 1 or x > 50:
        raise argparse.ArgumentTypeError("An integer between 1 and 50 is required")
    return x


def parse_args():
    """
    Parse command-line arguments.

    Returns:
        Tuple of (argparse.Namespace, list of unknown args).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "environment",
        help="Which environment to deploy to",
        nargs="*",
        type=str,
        default=["default"],
    )
    parser.add_argument(
        "--bucket-name",
        help="The bucket to upload files to",
        type=str,
    )
    parser.add_argument(
        "--local-path",
        help="The local folder to upload files from",
        type=str,
    )
    parser.add_argument(
        "--bucket-path",
        help="The remote folder to upload files to",
        type=str,
    )
    parser.add_argument(
        "--exclude",
        help="A filename or pattern to ignore. Can be set multiple times.",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--acl",
        help="The ACL to apply to uploaded files.",
        type=str,
        default=None,
        choices=VALID_ACLS,
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Upload all files whether they are currently up to date on S3 or not",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        help="Show which files would be updated without uploading to S3",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--charset",
        help="The charset header to add to text files",
        default=None,
    )
    parser.add_argument(
        "--gitignore",
        help="Add .gitignore rules to the exclude list",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-p",
        "--processes",
        help="The number of concurrent processes to use for uploading/deleting.",
        type=processes_int,
        default=10,
    )
    parser.add_argument(
        "--delete",
        help="Remove orphaned files from S3",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--confirm",
        help="Confirm each file before deleting. Only works when --delete is set.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--cloudfront-id",
        help=(
            "Specify one or more CloudFront distribution IDs to invalidate "
            "after updating."
        ),
        action="append",
        default=[],
    )
    parser.add_argument(
        "--all",
        help="Upload to all environments",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print the script version and exit",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to config file. Defaults to .d3ploy.json in current directory.",
        type=str,
        default=".d3ploy.json",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="Suppress all output. Useful for automated usage.",
        action="store_true",
        default=False,
    )

    return parser.parse_known_args()


def cli():
    """
    Main CLI entry point.

    This is called from __main__.py for Briefcase execution.
    """
    # Set up signal handlers
    signals.setup_signal_handlers()

    # Parse arguments
    args, unknown = parse_args()

    # Handle version flag early
    if args.version:
        operations.alert(
            f"d3ploy {__version__}",
            error_code=os.EX_OK,
            color=colorama.Fore.GREEN,
            quiet=args.quiet,
        )

    # Check for old deploy.json
    if pathlib.Path("deploy.json").exists():
        operations.alert(
            (
                "It looks like you have an old version of deploy.json in your project. "
                "Please visit https://github.com/dryan/d3ploy#readme for information "
                "on upgrading."
            ),
            error_code=os.EX_CONFIG,
            quiet=args.quiet,
        )

    # Load config file
    config = {}
    config_path = pathlib.Path(args.config)
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        operations.alert(
            (
                f"Config file is missing. Looked for {args.config}. "
                f"See http://dryan.github.io/d3ploy for more information."
            ),
            error_code=os.EX_NOINPUT,
            quiet=args.quiet,
        )

    environments = [f"{item}" for item in config.get("environments", {}).keys()]
    defaults = config.get("defaults", {})

    # Check if no environments are configured
    if not environments:
        operations.alert(
            f"No environments found in config file: {args.config}",
            error_code=os.EX_NOINPUT,
            quiet=args.quiet,
        )

    if args.all:
        args.environment = environments

    # Check if environment actually exists in the config file
    invalid_environments = []
    for env in args.environment:
        if env not in environments:
            invalid_environments.append(env)
    if invalid_environments:
        operations.alert(
            (
                f"environment{'' if len(invalid_environments) == 1 else 's'} "
                f"{', '.join(invalid_environments)} not found in config. "
                f'Choose from "{", ".join(environments)}"'
            ),
            error_code=os.EX_NOINPUT,
            quiet=args.quiet,
        )

    to_deploy = environments if args.all else args.environment

    # Check for updates
    try:
        updates.check_for_updates(__version__)
    except Exception as e:
        if os.environ.get("D3PLOY_DEBUG") == "True":
            raise e

    # Deploy to each environment
    for environ in to_deploy:
        operations.alert(
            f"Uploading environment {to_deploy.index(environ) + 1:d} "
            f"of {len(to_deploy):d}",
            quiet=args.quiet,
        )
        environ_config = config["environments"][environ]

        if not environ_config.get("excludes", False):
            environ_config["excludes"] = []
        if not defaults.get("excludes", False):
            defaults["excludes"] = []

        excludes = []
        if args.exclude:
            excludes = args.exclude
        else:
            excludes = environ_config.get("exclude", []) + defaults.get("exclude", [])
        excludes.append(args.config)

        operations.sync_environment(
            environ,
            bucket_name=args.bucket_name
            or environ_config.get("bucket_name")
            or defaults.get("bucket_name"),
            local_path=args.local_path
            or environ_config.get("local_path")
            or defaults.get("local_path")
            or ".",
            bucket_path=args.bucket_path
            or environ_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/",
            excludes=excludes,
            acl=args.acl or environ_config.get("acl") or defaults.get("acl"),
            force=args.force or environ_config.get("force") or defaults.get("force"),
            dry_run=args.dry_run,
            charset=args.charset
            or environ_config.get("charset")
            or defaults.get("charset"),
            gitignore=args.gitignore
            or environ_config.get("gitignore")
            or defaults.get("gitignore"),
            processes=args.processes,
            delete=args.delete
            or environ_config.get("delete")
            or defaults.get("delete"),
            confirm=args.confirm,
            cloudfront_id=args.cloudfront_id
            or environ_config.get("cloudfront_id")
            or defaults.get("cloudfront_id")
            or [],
            caches=environ_config.get("caches", {}) or defaults.get("caches", {}),
            quiet=args.quiet,
        )
