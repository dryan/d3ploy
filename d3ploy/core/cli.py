"""
Typer-based CLI for d3ploy.

Modern CLI with better help, type safety, and automatic documentation.
"""

import json
import os
import pathlib
import sys
from typing import Annotated
from typing import Optional

import typer
from rich.console import Console

from .. import __version__
from .. import config as config_module
from .. import ui
from ..sync import operations
from . import signals
from . import updates

app = typer.Typer(
    name="d3ploy",
    help="Deploy static sites to S3 with multiple environment support.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

VALID_ACLS = ["private", "public-read", "public-read-write", "authenticated-read"]


def version_callback(*, value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"d3ploy {__version__}", style="green")
        raise typer.Exit()


@app.callback()
def main(
    *,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Print the script version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """
    Deploy static sites to S3 with multiple environment support.
    """
    pass


@app.command()
def sync(
    targets: Annotated[
        Optional[list[str]],
        typer.Argument(
            help="Which target(s) to deploy to. Defaults to 'default'.",
            show_default=False,
        ),
    ] = None,
    *,
    bucket_name: Annotated[
        Optional[str],
        typer.Option(
            "--bucket-name",
            help="The bucket to upload files to.",
        ),
    ] = None,
    local_path: Annotated[
        Optional[str],
        typer.Option(
            "--local-path",
            help="The local folder to upload files from.",
        ),
    ] = None,
    bucket_path: Annotated[
        Optional[str],
        typer.Option(
            "--bucket-path",
            help="The remote folder to upload files to.",
        ),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        typer.Option(
            "--exclude",
            help="A filename or pattern to ignore. Can be set multiple times.",
        ),
    ] = None,
    acl: Annotated[
        Optional[str],
        typer.Option(
            "--acl",
            help="The ACL to apply to uploaded files.",
            case_sensitive=False,
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Upload all files whether they are currently up to date on S3 or not.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Show which files would be updated without uploading to S3.",
        ),
    ] = False,
    charset: Annotated[
        Optional[str],
        typer.Option(
            "--charset",
            help="The charset header to add to text files.",
        ),
    ] = None,
    gitignore: Annotated[
        bool,
        typer.Option(
            "--gitignore",
            help="Add .gitignore rules to the exclude list.",
        ),
    ] = False,
    processes: Annotated[
        int,
        typer.Option(
            "--processes",
            "-p",
            help="The number of concurrent processes to use for uploading/deleting.",
            min=1,
            max=50,
        ),
    ] = 10,
    delete: Annotated[
        bool,
        typer.Option(
            "--delete",
            help="Remove orphaned files from S3.",
        ),
    ] = False,
    confirm: Annotated[
        bool,
        typer.Option(
            "--confirm",
            help="Confirm each file before deleting. Only works when --delete is set.",
        ),
    ] = False,
    cloudfront_id: Annotated[
        Optional[list[str]],
        typer.Option(
            "--cloudfront-id",
            help="Specify one or more CloudFront distribution IDs to invalidate after updating.",
        ),
    ] = None,
    all_targets: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Upload to all targets.",
        ),
    ] = False,
    config: Annotated[
        str,
        typer.Option(
            "--config",
            "-c",
            help="Path to config file.",
        ),
    ] = ".d3ploy.json",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress all output. Useful for automated usage.",
        ),
    ] = False,
) -> None:
    """
    Deploy static sites to Amazon S3 with multiple environment support.

    Supports features like file exclusion patterns, .gitignore support,
    CloudFront invalidation, cache control headers, parallel uploads,
    dry-run mode, and file deletion sync.
    """
    # Set up signal handlers
    signals.setup_signal_handlers()

    # Validate ACL if provided
    if acl and acl not in VALID_ACLS:
        console.print(
            f"[red]Invalid ACL:[/red] {acl}. Must be one of: {', '.join(VALID_ACLS)}",
        )
        raise typer.Exit(code=os.EX_USAGE)

    # Normalize exclude and cloudfront_id to lists
    exclude = exclude or []
    cloudfront_id = cloudfront_id or []

    # Normalize targets
    if targets is None:
        targets = ["default"]

    # Detect if we should prompt interactively for target selection
    is_interactive = hasattr(sys, "ps1") or sys.stdin.isatty()
    no_target_specified = targets == ["default"] and not all_targets
    config_path = pathlib.Path(config)
    has_config = config_path.exists()
    should_prompt_for_target = (
        is_interactive and not quiet and no_target_specified and has_config
    )

    if should_prompt_for_target:
        # Show interactive target selection
        from ..ui import prompts

        selected_target = prompts.select_target(config_path=config)
        if selected_target is None:
            # User cancelled
            raise typer.Exit()
        targets = [selected_target]

    # CLI mode - require all necessary parameters
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
            quiet=quiet,
        )

    # Load config file (if it exists)
    config_data = {}
    config_exists = config_path.exists()

    if config_exists:
        config_data = json.loads(config_path.read_text())

        # Check if migration is needed
        if config_module.needs_migration(config_data):
            old_version = config_data.get("version", 0)
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
                f"  {config_module.get_migration_command(config)}",
                level="info",
                quiet=False,
            )
            raise typer.Exit(code=os.EX_CONFIG)

    target_list = [f"{item}" for item in config_data.get("targets", {}).keys()]
    defaults = config_data.get("defaults", {})

    # Check if user provided enough information to proceed without config
    has_required_args = bucket_name is not None

    if not config_exists and not has_required_args:
        operations.alert(
            (
                f"Config file is missing. Looked for {config}. "
                f"See http://dryan.github.io/d3ploy for more information."
            ),
            error_code=os.EX_NOINPUT,
            quiet=quiet,
        )

    # If no config and user provided bucket_name, allow running without config
    if not config_exists and has_required_args:
        # Create a minimal synthetic target
        target_list = targets if targets != ["default"] else ["cli"]
        targets = target_list  # Update targets to match the synthetic targets
        config_data = {"targets": {}, "defaults": {}}
        for t in target_list:
            config_data["targets"][t] = {}
        defaults = {}
    elif config_exists:
        # Check if no targets are configured
        if not target_list:
            operations.alert(
                f"No targets found in config file: {config}",
                error_code=os.EX_NOINPUT,
                quiet=quiet,
            )

        if all_targets:
            targets = target_list

        # Check if target actually exists in the config file
        if not has_required_args:
            invalid_targets = []
            for target in targets:
                if target not in target_list:
                    invalid_targets.append(target)
            if invalid_targets:
                operations.alert(
                    (
                        f"target{'' if len(invalid_targets) == 1 else 's'} "
                        f"{', '.join(invalid_targets)} not found in config. "
                        f'Choose from "{", ".join(target_list)}"'
                    ),
                    error_code=os.EX_NOINPUT,
                    quiet=quiet,
                )

    to_deploy = target_list if all_targets else targets

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
            quiet=quiet,
        )
        target_config = config_data.get("targets", {}).get(target, {})

        if not target_config.get("excludes", False):
            target_config["excludes"] = []
        if not defaults.get("excludes", False):
            defaults["excludes"] = []

        excludes = []
        if exclude:
            excludes = exclude
        else:
            excludes = target_config.get("exclude", []) + defaults.get("exclude", [])
        if config_exists:
            excludes.append(config)

        bucket = (
            bucket_name
            or target_config.get("bucket_name")
            or defaults.get("bucket_name")
        )
        operations.sync_target(
            target,
            bucket_name=bucket,
            local_path=local_path
            or target_config.get("local_path")
            or defaults.get("local_path")
            or ".",
            bucket_path=bucket_path
            or target_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/",
            excludes=excludes,
            acl=acl or target_config.get("acl") or defaults.get("acl"),
            force=force or target_config.get("force") or defaults.get("force"),
            dry_run=dry_run,
            charset=charset or target_config.get("charset") or defaults.get("charset"),
            gitignore=gitignore
            or target_config.get("gitignore")
            or defaults.get("gitignore"),
            processes=processes,
            delete=delete or target_config.get("delete") or defaults.get("delete"),
            confirm=confirm,
            cloudfront_id=cloudfront_id
            or target_config.get("cloudfront_id")
            or defaults.get("cloudfront_id")
            or [],
            caches=target_config.get("caches", {}) or defaults.get("caches", {}),
            quiet=quiet,
            using_config=config_exists,
        )


@app.command()
def migrate_config(
    config_path: Annotated[
        str,
        typer.Argument(
            help="Path to config file to migrate.",
        ),
    ],
) -> None:
    """
    Migrate a config file to the latest version.

    This command will update your configuration file to the current version,
    making a backup of the original file first.
    """
    path = pathlib.Path(config_path)
    if not path.exists():
        console.print(f"[red]Config file not found:[/red] {config_path}")
        raise typer.Exit(code=os.EX_NOINPUT)

    try:
        config = json.loads(path.read_text())
        if not config_module.needs_migration(config):
            console.print(
                f"[green]✓[/green] Config file {config_path} is already at version {config_module.CURRENT_VERSION}",
            )
            raise typer.Exit()

        # Show what will change
        old_version = config.get("version", 0)
        console.print(
            f"[yellow]Migrating config from version {old_version} to {config_module.CURRENT_VERSION}...[/yellow]",
        )

        # Perform migration
        migrated = config_module.migrate_config(config)

        # Show changes
        if "environments" in config and "targets" in migrated:
            console.print("  [cyan]•[/cyan] Renamed 'environments' → 'targets'")

        # Save migrated config
        config_module.save_migrated_config(migrated, path=config_path)
        console.print(
            f"[green]✓ Config file {config_path} migrated successfully[/green]",
        )
    except Exception as e:
        console.print(f"[red]Error migrating config:[/red] {e}")
        raise typer.Exit(code=os.EX_DATAERR)


def cli() -> None:
    """
    Main CLI entry point.

    This is called from __main__.py for Briefcase execution.
    Implements default command behavior for backward compatibility.
    """
    # If no subcommand provided, default to 'sync'
    if len(sys.argv) == 1 or (
        len(sys.argv) > 1
        and sys.argv[1] not in ["sync", "migrate-config"]
        and not sys.argv[1].startswith("-")
    ):
        # Insert 'sync' as the command
        sys.argv.insert(1, "sync")

    app()
