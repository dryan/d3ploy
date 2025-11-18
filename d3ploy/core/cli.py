"""
CLI argument parsing and main entry point.
"""

import argparse
import json
import os
import pathlib
import sys
from typing import Union

from .. import __version__
from .. import config as config_module
from .. import ui
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
        "target",
        help="Which target to deploy to",
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
        help="Upload to all targets",
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
    parser.add_argument(
        "--no-tui",
        help="Disable TUI mode and use CLI fallback (requires all parameters).",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--migrate-config",
        help="Migrate a config file to the latest version.",
        metavar="PATH",
        type=str,
        default=None,
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
        ui.output.display_message(
            f"d3ploy {__version__}",
            level="success",
            quiet=args.quiet,
        )
        sys.exit(os.EX_OK)

    # Handle config migration flag
    if args.migrate_config:
        config_path = pathlib.Path(args.migrate_config)
        if not config_path.exists():
            ui.output.display_error(
                f"Config file not found: {args.migrate_config}",
                exit_code=os.EX_NOINPUT,
            )

        try:
            config = json.loads(config_path.read_text())
            if not config_module.needs_migration(config):
                ui.output.display_message(
                    f"Config file {args.migrate_config} is already at version {config_module.CURRENT_VERSION}",
                    level="success",
                )
                sys.exit(os.EX_OK)

            # Show what will change
            old_version = config.get("version", 0)
            ui.output.display_message(
                f"Migrating config from version {old_version} to {config_module.CURRENT_VERSION}...",
                level="info",
            )

            # Perform migration
            migrated = config_module.migrate_config(config)

            # Show changes
            if "environments" in config and "targets" in migrated:
                ui.output.display_message(
                    "  - Renamed 'environments' → 'targets'",
                    level="info",
                )

            # Save migrated config
            config_module.save_migrated_config(migrated, path=args.migrate_config)
            ui.output.display_message(
                f"✓ Config file {args.migrate_config} migrated successfully",
                level="success",
            )
            sys.exit(os.EX_OK)
        except Exception as e:
            ui.output.display_error(
                f"Error migrating config: {e}",
                exit_code=os.EX_DATAERR,
            )

    # Detect if we should use TUI mode
    # Use TUI if:
    # 1. Terminal is interactive (has ps1 prompt, more reliable than isatty)
    # 2. Not in quiet mode
    # 3. --no-tui flag not set
    # 4. No target specified (let user choose interactively)
    # 5. Config file exists (TUI requires config)
    is_interactive = hasattr(sys, "ps1") or sys.stdin.isatty()
    no_target_specified = args.target == ["default"] and not args.all
    config_path = pathlib.Path(args.config)
    has_config = config_path.exists()
    should_use_tui = (
        is_interactive
        and not args.quiet
        and not args.no_tui
        and no_target_specified
        and has_config
    )

    if should_use_tui:
        # Launch TUI mode
        from ..ui import tui

        return tui.run_tui(config_path=args.config)

    # CLI fallback mode - require all necessary parameters
    # If we're in non-interactive mode and missing target, error out
    if not is_interactive and no_target_specified:
        ui.output.display_error(
            "Error: No target specified. In non-interactive mode, "
            "you must specify a target or use --all.",
            exit_code=os.EX_USAGE,
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

    # Load config file (if it exists)
    config = {}
    config_path = pathlib.Path(args.config)
    config_exists = config_path.exists()

    if config_exists:
        config = json.loads(config_path.read_text())

        # Check if migration is needed
        if config_module.needs_migration(config):
            old_version = config.get("version", 0)
            ui.output.display_message(
                f"Your config file is version {old_version} but d3ploy now requires version {config_module.CURRENT_VERSION}.",
                level="error",
                quiet=False,
            )
            ui.output.display_message(
                "\nTo migrate your config file, run:",
                level="info",
                quiet=False,
            )
            ui.output.display_message(
                f"  {config_module.get_migration_command(args.config)}",
                level="info",
                quiet=False,
            )
            sys.exit(os.EX_CONFIG)

    targets = [f"{item}" for item in config.get("targets", {}).keys()]
    defaults = config.get("defaults", {})

    # Check if user provided enough information to proceed without config
    has_required_args = args.bucket_name is not None

    if not config_exists and not has_required_args:
        operations.alert(
            (
                f"Config file is missing. Looked for {args.config}. "
                f"See http://dryan.github.io/d3ploy for more information."
            ),
            error_code=os.EX_NOINPUT,
            quiet=args.quiet,
        )

    # If no config and user provided bucket_name, allow running without config
    if not config_exists and has_required_args:
        # Create a minimal synthetic target
        targets = args.target if args.target != ["default"] else ["cli"]
        args.target = targets  # Update args.target to match the synthetic targets
        config = {"targets": {}, "defaults": {}}
        for t in targets:
            config["targets"][t] = {}
        defaults = {}
    elif config_exists:
        # Check if no targets are configured
        if not targets:
            operations.alert(
                f"No targets found in config file: {args.config}",
                error_code=os.EX_NOINPUT,
                quiet=args.quiet,
            )

        if args.all:
            args.target = targets

        # Check if target actually exists in the config file (only if not providing bucket_name)
        if not has_required_args:
            invalid_targets = []
            for target in args.target:
                if target not in targets:
                    invalid_targets.append(target)
            if invalid_targets:
                operations.alert(
                    (
                        f"target{'' if len(invalid_targets) == 1 else 's'} "
                        f"{', '.join(invalid_targets)} not found in config. "
                        f'Choose from "{", ".join(targets)}"'
                    ),
                    error_code=os.EX_NOINPUT,
                    quiet=args.quiet,
                )

    to_deploy = targets if args.all else args.target

    # Check for updates
    try:
        updates.check_for_updates(__version__)
    except Exception as e:
        if os.environ.get("D3PLOY_DEBUG") == "True":
            raise e

    # Deploy to each target
    for target in to_deploy:
        operations.alert(
            f"Uploading target {to_deploy.index(target) + 1:d} of {len(to_deploy):d}",
            quiet=args.quiet,
        )
        target_config = config.get("targets", {}).get(target, {})

        if not target_config.get("excludes", False):
            target_config["excludes"] = []
        if not defaults.get("excludes", False):
            defaults["excludes"] = []

        excludes = []
        if args.exclude:
            excludes = args.exclude
        else:
            excludes = target_config.get("exclude", []) + defaults.get("exclude", [])
        if config_exists:
            excludes.append(args.config)

        bucket_name = (
            args.bucket_name
            or target_config.get("bucket_name")
            or defaults.get("bucket_name")
        )
        operations.sync_target(
            target,
            bucket_name=bucket_name,
            local_path=args.local_path
            or target_config.get("local_path")
            or defaults.get("local_path")
            or ".",
            bucket_path=args.bucket_path
            or target_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/",
            excludes=excludes,
            acl=args.acl or target_config.get("acl") or defaults.get("acl"),
            force=args.force or target_config.get("force") or defaults.get("force"),
            dry_run=args.dry_run,
            charset=args.charset
            or target_config.get("charset")
            or defaults.get("charset"),
            gitignore=args.gitignore
            or target_config.get("gitignore")
            or defaults.get("gitignore"),
            processes=args.processes,
            delete=args.delete or target_config.get("delete") or defaults.get("delete"),
            confirm=args.confirm,
            cloudfront_id=args.cloudfront_id
            or target_config.get("cloudfront_id")
            or defaults.get("cloudfront_id")
            or [],
            caches=target_config.get("caches", {}) or defaults.get("caches", {}),
            quiet=args.quiet,
            using_config=config_exists,
        )
