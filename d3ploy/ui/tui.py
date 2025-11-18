"""
Textual TUI application for d3ploy.

This is the default interface when running d3ploy in an interactive terminal.
"""

import os
from typing import Optional

from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import Static

from d3ploy import config as config_module


class MigrationConfirmScreen(Screen):
    """
    Modal screen to confirm config migration.
    """

    def __init__(
        self,
        *,
        config_path: str,
        old_version: int,
        new_version: int,
    ):
        """
        Initialize migration confirmation screen.

        Args:
            config_path: Path to config file.
            old_version: Current config version.
            new_version: Target config version.
        """
        super().__init__()
        self.config_path = config_path
        self.old_version = old_version
        self.new_version = new_version

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Container(
            Static("Config Migration Required", classes="title"),
            Static(
                f"Your config file is version {self.old_version} but d3ploy "
                f"now requires version {self.new_version}.\n\n"
                f"This will update your config file:\n"
                f"  {self.config_path}\n\n"
                "Changes:\n"
                "  • Rename 'environments' → 'targets'\n"
                "  • Update version number\n\n"
                "Do you want to migrate your config file now?",
                id="migration-message",
            ),
            Container(
                Button("Yes, Migrate", id="migrate-yes", variant="primary"),
                Button("No, Exit", id="migrate-no", variant="error"),
                id="migration-buttons",
            ),
            id="migration-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "migrate-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class TargetSelectionScreen(Screen):
    """
    Main screen for selecting which target to deploy.

    Shows available targets from config and allows selection.
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
        Binding("s", "settings", "Settings"),
    ]

    def __init__(self, *, config_data: dict, config_path: Optional[str] = None):
        """
        Initialize target selection screen.

        Args:
            config_data: Loaded configuration dictionary.
            config_path: Path to config file.
        """
        super().__init__()
        self.config_data = config_data
        self.config_path = config_path

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Static("Select a target to deploy:", classes="title"),
            Container(*self._get_target_buttons(), id="target-list"),
            id="main-container",
        )
        yield Footer()

    def _get_target_buttons(self) -> list:
        """Create list of target buttons."""
        buttons = []

        targets = self.config_data.get("targets", {})
        if not targets:
            return [Label("No targets configured")]

        for target_name, target_config in targets.items():
            bucket = target_config.get("bucket_name") or self.config_data.get(
                "defaults", {}
            ).get("bucket_name", "")
            path = target_config.get("bucket_path", "/")

            button = Button(
                f"{target_name}\n{bucket}{path}",
                id=f"target-{target_name}",
                classes="target-button",
            )
            button.target_name = target_name  # Store for later
            buttons.append(button)

        return buttons

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle target button press."""
        if hasattr(event.button, "target_name"):
            target_name = event.button.target_name
            # Navigate to sync screen with selected target
            self.app.push_screen(
                SyncProgressScreen(
                    target=target_name,
                    config_data=self.config_data,
                    args={},  # No CLI args in pure TUI mode
                )
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_help(self) -> None:
        """Show help screen."""
        self.app.push_screen(HelpScreen())

    def action_settings(self) -> None:
        """Show settings screen."""
        self.app.push_screen(
            SettingsScreen(
                config_data=self.config_data,
                config_path=self.config_path,
            )
        )


class SyncProgressScreen(Screen):
    """
    Screen showing real-time sync progress.

    Displays files being synced, progress bars, and status updates.
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(
        self,
        *,
        target: str,
        config_data: dict,
        args: Optional[dict] = None,
    ):
        """
        Initialize sync progress screen.

        Args:
            target: Name of target being deployed.
            config_data: Configuration dictionary.
            args: Additional CLI arguments to pass through.
        """
        super().__init__()
        self.target = target
        self.config_data = config_data
        self.args = args or {}
        self._sync_complete = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Static(f"Deploying to: {self.target}", classes="title"),
            Static("Preparing to sync...", id="sync-status"),
            Container(id="progress-container"),
            id="main-container",
        )
        yield Footer()

    async def on_mount(self) -> None:
        """Handle screen mount - start sync operation."""
        from ..sync import operations

        status_widget = self.query_one("#sync-status", Static)
        status_widget.update("Starting deployment...")

        # Get target config
        target_config = self.config_data["targets"][self.target]
        defaults = self.config_data.get("defaults", {})

        # Build excludes list
        excludes = (
            target_config.get("exclude", [])
            + defaults.get("exclude", [])
            + self.args.get("exclude", [])
        )

        # Prepare sync parameters
        bucket_name = (
            self.args.get("bucket_name")
            or target_config.get("bucket_name")
            or defaults.get("bucket_name")
        )
        local_path = (
            self.args.get("local_path")
            or target_config.get("local_path")
            or defaults.get("local_path")
            or "."
        )
        bucket_path = (
            self.args.get("bucket_path")
            or target_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/"
        )

        try:
            # Run sync operation
            # TODO: Make this async and show real-time progress
            status_widget.update(f"Syncing to {bucket_name}{bucket_path}...")

            results = operations.sync_target(
                self.target,
                bucket_name=bucket_name,
                local_path=local_path,
                bucket_path=bucket_path,
                excludes=excludes,
                acl=self.args.get("acl")
                or target_config.get("acl")
                or defaults.get("acl"),
                force=self.args.get("force", False)
                or target_config.get("force", False)
                or defaults.get("force", False),
                dry_run=self.args.get("dry_run", False),
                charset=self.args.get("charset")
                or target_config.get("charset")
                or defaults.get("charset"),
                gitignore=self.args.get("gitignore", False)
                or target_config.get("gitignore", False)
                or defaults.get("gitignore", False),
                processes=self.args.get("processes", 10),
                delete=self.args.get("delete", False)
                or target_config.get("delete", False)
                or defaults.get("delete", False),
                confirm=self.args.get("confirm", False),
                cloudfront_id=self.args.get("cloudfront_id", [])
                or target_config.get("cloudfront_id", [])
                or defaults.get("cloudfront_id", []),
                caches=target_config.get("caches", {}) or defaults.get("caches", {}),
                quiet=False,  # Don't suppress in TUI
            )

            self._sync_complete = True
            status_widget.update(
                f"[green]✓[/green] Deployment complete!\n\n"
                f"Uploaded: {results.get('uploaded', 0)} files\n"
                f"Deleted: {results.get('deleted', 0)} files\n"
                f"Invalidated: {results.get('invalidated', 0)} paths"
            )

        except Exception as e:
            status_widget.update(f"[red]✗[/red] Error: {e}")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to target selection."""
        if self._sync_complete:
            self.app.pop_screen()
        else:
            # TODO: Ask for confirmation if sync in progress
            self.app.pop_screen()


class HelpScreen(Screen):
    """
    Screen showing keyboard shortcuts and help information.
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Static("d3ploy Help", classes="title"),
            Static(
                """
Keyboard Shortcuts:
-------------------
q          - Quit application
h          - Show this help screen
s          - Show settings
Escape     - Go back to previous screen
Enter      - Select/Confirm
Arrow Keys - Navigate

About d3ploy:
-------------
d3ploy syncs local files to AWS S3 with support for
multiple targets, CloudFront invalidation, and
intelligent file change detection.
                """,
                id="help-content",
            ),
            id="main-container",
        )
        yield Footer()

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()


class SettingsScreen(Screen):
    """
    Screen for viewing and editing configuration.
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, *, config_data: dict, config_path: Optional[str] = None):
        """
        Initialize settings screen.

        Args:
            config_data: Configuration dictionary.
            config_path: Path to config file.
        """
        super().__init__()
        self.config_data = config_data
        self.config_path = config_path

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Static("Settings", classes="title"),
            Static(
                f"Config file: {self.config_path or 'Not specified'}\n\n"
                "Configuration viewer/editor will be implemented here.",
                id="settings-content",
            ),
            id="main-container",
        )
        yield Footer()

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()


class D3ployTUI(App):
    """
    Main Textual application for d3ploy.

    This is the default interface when running in an interactive terminal.
    """

    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 80%;
        height: auto;
        padding: 2;
        border: solid $primary;
        background: $surface;
    }

    .title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #target-list {
        layout: vertical;
        height: auto;
        margin-top: 1;
    }

    .target-button {
        width: 100%;
        margin: 1;
        min-height: 3;
    }

    #help-content, #settings-content, #sync-status {
        padding: 1;
        margin-top: 1;
    }

    /* Migration dialog styles */
    #migration-dialog {
        width: 60;
        height: auto;
        padding: 2;
        border: solid $warning;
        background: $surface;
    }

    #migration-message {
        padding: 1;
        margin-bottom: 1;
    }

    #migration-buttons {
        layout: horizontal;
        height: auto;
        align: center middle;
    }

    #migration-buttons Button {
        margin: 0 1;
    }
    """

    TITLE = "d3ploy - AWS S3 Deployment Tool"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
    ]

    def __init__(self, *, config_path: Optional[str] = None):
        """
        Initialize the TUI application.

        Args:
            config_path: Optional path to config file.
        """
        super().__init__()
        self.config_path = config_path
        self.config_data = None
        self._exit_code = os.EX_OK

    def exit(
        self,
        result: object = None,
        *,
        return_code: int = os.EX_OK,
        message: str | None = None,
    ) -> None:
        """
        Exit the application with optional return code and message.

        Args:
            result: Result to return from run().
            return_code: Exit code (default: 0).
            message: Optional message to display.
        """
        self._exit_code = return_code
        super().exit(result=message if message else result)

    def on_mount(self) -> None:
        """Handle application mount event."""
        # Load configuration
        try:
            self.config_data = config_module.load_config(self.config_path)

            # Check if migration is needed
            if config_module.needs_migration(self.config_data):
                old_version = self.config_data.get("version", 0)

                async def handle_migration_response(migrate: bool) -> None:
                    """Handle user's migration decision."""
                    if not migrate:
                        self.exit(
                            return_code=os.EX_CONFIG,
                            message="Config migration declined. Exiting.",
                        )
                        return

                    try:
                        # Perform migration
                        migrated = config_module.migrate_config(self.config_data)

                        # Save to disk
                        config_module.save_migrated_config(
                            migrated,
                            path=self.config_path or ".d3ploy.json",
                        )

                        # Use migrated config
                        self.config_data = migrated

                        # Continue to target selection
                        self.push_screen(
                            TargetSelectionScreen(
                                config_data=self.config_data,
                                config_path=self.config_path,
                            )
                        )
                    except Exception as e:
                        self.exit(
                            return_code=os.EX_CONFIG,
                            message=f"Error migrating config: {e}",
                        )

                # Show migration confirmation dialog
                self.push_screen(
                    MigrationConfirmScreen(
                        config_path=self.config_path or ".d3ploy.json",
                        old_version=old_version,
                        new_version=config_module.CURRENT_VERSION,
                    ),
                    handle_migration_response,
                )
                return

        except FileNotFoundError as e:
            self.exit(return_code=os.EX_NOINPUT, message=f"Error: {e}")
            return
        except Exception as e:
            self.exit(return_code=os.EX_CONFIG, message=f"Error loading config: {e}")
            return

        # Push the target selection screen
        self.push_screen(
            TargetSelectionScreen(
                config_data=self.config_data,
                config_path=self.config_path,
            )
        )

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run_tui(*, config_path: Optional[str] = None) -> int:
    """
    Run the Textual TUI application.

    Args:
        config_path: Optional path to config file.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    app = D3ployTUI(config_path=config_path)
    result = app.run()

    # Handle exit messages and return codes
    if result and isinstance(result, str):
        print(result)
        # If there was an error message, assume non-zero exit
        return getattr(app, "_exit_code", os.EX_SOFTWARE)

    return getattr(app, "_exit_code", os.EX_OK)
