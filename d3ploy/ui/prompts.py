"""
Rich-based interactive prompts for d3ploy.

Provides keyboard-selectable menus and interactive configuration
for terminal environments that support it.
"""

from typing import Optional

from rich.console import Console
from rich.prompt import Confirm
from rich.prompt import Prompt
from rich.table import Table

from d3ploy import config as config_module

# Valid ACL options for S3
VALID_ACLS = ["private", "public-read", "public-read-write", "authenticated-read"]


def select_target(*, config_path: str) -> Optional[str]:
    """
    Display an interactive target selection menu.

    Args:
        config_path: Path to the config file.

    Returns:
        Selected target name, or None if user cancels.
    """
    console = Console()

    # Load config
    try:
        config_data = config_module.loader.load_config(config_path=config_path)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        return None

    targets = config_data.get("targets", {})
    if not targets:
        console.print("[yellow]No targets found in config file.[/yellow]")
        return None

    # Display targets in a nice table
    table = Table(title="Available Targets", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Target Name", style="cyan")
    table.add_column("Bucket", style="green")
    table.add_column("Local Path", style="yellow")

    target_list = list(targets.items())
    for idx, (target_name, target_config) in enumerate(target_list, 1):
        bucket = target_config.get("bucket_name", "")
        local_path = target_config.get("local_path", ".")
        table.add_row(str(idx), target_name, bucket, local_path)

    console.print()
    console.print(table)
    console.print()

    # Prompt for selection
    while True:
        choice = Prompt.ask(
            "Select a target by number (or 'q' to quit)",
            default="1",
        )

        if choice.lower() in ("q", "quit", "exit"):
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(target_list):
                selected_target = target_list[idx][0]
                console.print(f"[green]✓[/green] Selected: {selected_target}")
                return selected_target
            console.print(
                f"[red]Invalid choice. Please enter a number between 1 and {len(target_list)}[/red]",  # noqa: E501
            )
        except ValueError:
            console.print(
                "[red]Invalid input. Please enter a number or 'q' to quit[/red]"
            )


def confirm_config_migration(
    *,
    config_path: str,
    old_version: int,
    new_version: int,
) -> bool:
    """
    Ask user to confirm config file migration.

    Args:
        config_path: Path to the config file.
        old_version: Current config version.
        new_version: Target config version.

    Returns:
        True if user confirms migration, False otherwise.
    """
    console = Console()

    console.print()
    console.print("[yellow]⚠ Configuration Update Required[/yellow]")
    console.print()
    console.print(f"Your config file is version {old_version}.")
    console.print(f"The current version is {new_version}.")
    console.print()
    console.print(f"Config file: [cyan]{config_path}[/cyan]")
    console.print()
    console.print("Your config file needs to be migrated to the new format.")
    console.print("A backup will be created automatically.")
    console.print()

    return Confirm.ask(
        "Would you like to migrate your config now?",
        default=True,
    )


def prompt_for_bucket_config() -> Optional[dict]:
    """
    Interactively prompt for basic bucket configuration.

    Used when no config file exists and user wants to deploy.

    Returns:
        Dictionary with bucket configuration, or None if user cancels.
    """
    console = Console()

    console.print()
    console.print("[cyan]No configuration file found.[/cyan]")
    console.print("Let's set up your deployment configuration.")
    console.print()

    bucket_name = Prompt.ask("S3 Bucket name")
    if not bucket_name:
        return None

    local_path = Prompt.ask("Local path to deploy", default=".")

    bucket_path = Prompt.ask("Bucket path (subfolder in S3)", default="")

    # Ask about optional settings
    console.print()
    console.print("Optional settings (press Enter to skip):")
    console.print()

    acl = Prompt.ask(
        "ACL (access control)",
        default="public-read",
        choices=VALID_ACLS,
    )

    # Ask if they want to save config
    console.print()
    save_config = Confirm.ask(
        "Save these settings to d3ploy.json?",
        default=True,
    )

    return {
        "bucket_name": bucket_name,
        "local_path": local_path,
        "bucket_path": bucket_path,
        "acl": acl,
        "save_config": save_config,
    }


def confirm_destructive_operation(
    *,
    operation: str,
    file_count: int | None = None,
) -> bool:
    """
    Ask user to confirm a destructive operation.

    Args:
        operation: Description of the operation (e.g., "delete files").
        file_count: Optional number of files that will be affected.

    Returns:
        True if user confirms, False otherwise.
    """
    console = Console()

    console.print()
    console.print("[yellow]⚠ Warning: Destructive Operation[/yellow]")
    console.print()

    if file_count is not None:
        console.print(
            f"This will {operation} affecting [red]{file_count}[/red] file(s)."
        )
    else:
        console.print(f"This will {operation}.")

    console.print()

    return Confirm.ask(
        "Do you want to proceed?",
        default=False,
    )


def prompt_for_acl() -> str:
    """
    Prompt user to select an ACL.

    Returns:
        Selected ACL value.
    """
    console = Console()

    console.print()
    console.print(
        "[cyan]Select an ACL (Access Control List) for uploaded files:[/cyan]"
    )
    console.print()

    # Show options
    acl_descriptions = {
        "private": "Private - Only owner has access",
        "public-read": "Public Read - Anyone can read, owner can write",
        "public-read-write": "Public Read/Write - Anyone can read and write",
        "authenticated-read": "Authenticated Read - AWS users can read",
    }

    for idx, (acl, description) in enumerate(acl_descriptions.items(), 1):
        console.print(f"  [cyan]{idx}.[/cyan] {acl:20s} - {description}")

    console.print()

    while True:
        choice = Prompt.ask(
            "Select ACL by number or name",
            default="2",
        )

        # Try as number first
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(VALID_ACLS):
                return VALID_ACLS[idx]
        except ValueError:
            # Try as ACL name
            if choice in VALID_ACLS:
                return choice

        console.print("[red]Invalid choice. Please try again.[/red]")
        console.print()
