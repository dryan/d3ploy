"""
Textual TUI application for d3ploy.

This is the default interface when running d3ploy in an interactive terminal.
"""

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


class EnvironmentSelectionScreen(Screen):
    """
    Main screen for selecting which environment to deploy.

    Shows available environments from config and allows selection.
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "help", "Help"),
        Binding("s", "settings", "Settings"),
    ]

    def __init__(self, *, config_data: dict, config_path: Optional[str] = None):
        """
        Initialize environment selection screen.

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
            Static("Select an environment to deploy:", classes="title"),
            Container(*self._get_environment_buttons(), id="environment-list"),
            id="main-container",
        )
        yield Footer()

    def _get_environment_buttons(self) -> list:
        """Create list of environment buttons."""
        buttons = []

        environments = self.config_data.get("environments", {})
        if not environments:
            return [Label("No environments configured")]

        for env_name, env_config in environments.items():
            bucket = env_config.get("bucket_name") or self.config_data.get(
                "defaults", {}
            ).get("bucket_name", "")
            path = env_config.get("bucket_path", "/")

            button = Button(
                f"{env_name}\n{bucket}{path}",
                id=f"env-{env_name}",
                classes="environment-button",
            )
            button.env_name = env_name  # Store for later
            buttons.append(button)

        return buttons

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle environment button press."""
        if hasattr(event.button, "env_name"):
            env_name = event.button.env_name
            # Navigate to sync screen with selected environment
            self.app.push_screen(
                SyncProgressScreen(
                    environment=env_name,
                    config_data=self.config_data,
                    args={},  # No CLI args in pure TUI mode
                )
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Implement help screen
        self.app.bell()

    def action_settings(self) -> None:
        """Show settings screen."""
        # TODO: Implement settings screen
        self.app.bell()


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
        environment: str,
        config_data: dict,
        args: Optional[dict] = None,
    ):
        """
        Initialize sync progress screen.

        Args:
            environment: Name of environment being deployed.
            config_data: Configuration dictionary.
            args: Additional CLI arguments to pass through.
        """
        super().__init__()
        self.environment = environment
        self.config_data = config_data
        self.args = args or {}
        self._sync_complete = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield Container(
            Static(f"Deploying to: {self.environment}", classes="title"),
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

        # Get environment config
        env_config = self.config_data["environments"][self.environment]
        defaults = self.config_data.get("defaults", {})

        # Build excludes list
        excludes = (
            env_config.get("exclude", [])
            + defaults.get("exclude", [])
            + self.args.get("exclude", [])
        )

        # Prepare sync parameters
        bucket_name = (
            self.args.get("bucket_name")
            or env_config.get("bucket_name")
            or defaults.get("bucket_name")
        )
        local_path = (
            self.args.get("local_path")
            or env_config.get("local_path")
            or defaults.get("local_path")
            or "."
        )
        bucket_path = (
            self.args.get("bucket_path")
            or env_config.get("bucket_path")
            or defaults.get("bucket_path")
            or "/"
        )

        try:
            # Run sync operation
            # TODO: Make this async and show real-time progress
            status_widget.update(f"Syncing to {bucket_name}{bucket_path}...")

            results = operations.sync_environment(
                self.environment,
                bucket_name=bucket_name,
                local_path=local_path,
                bucket_path=bucket_path,
                excludes=excludes,
                acl=self.args.get("acl")
                or env_config.get("acl")
                or defaults.get("acl"),
                force=self.args.get("force", False)
                or env_config.get("force", False)
                or defaults.get("force", False),
                dry_run=self.args.get("dry_run", False),
                charset=self.args.get("charset")
                or env_config.get("charset")
                or defaults.get("charset"),
                gitignore=self.args.get("gitignore", False)
                or env_config.get("gitignore", False)
                or defaults.get("gitignore", False),
                processes=self.args.get("processes", 10),
                delete=self.args.get("delete", False)
                or env_config.get("delete", False)
                or defaults.get("delete", False),
                confirm=self.args.get("confirm", False),
                cloudfront_id=self.args.get("cloudfront_id", [])
                or env_config.get("cloudfront_id", [])
                or defaults.get("cloudfront_id", []),
                caches=env_config.get("caches", {}) or defaults.get("caches", {}),
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
        """Go back to environment selection."""
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
multiple environments, CloudFront invalidation, and
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

    #environment-list {
        layout: vertical;
        height: auto;
        margin-top: 1;
    }

    .environment-button {
        width: 100%;
        margin: 1;
        min-height: 3;
    }

    #help-content, #settings-content, #sync-status {
        padding: 1;
        margin-top: 1;
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

    def on_mount(self) -> None:
        """Handle application mount event."""
        # Load configuration
        try:
            self.config_data = config_module.load_config(self.config_path)
        except FileNotFoundError as e:
            self.exit(message=f"Error: {e}")
            return
        except Exception as e:
            self.exit(message=f"Error loading config: {e}")
            return

        # Push the environment selection screen
        self.push_screen(
            EnvironmentSelectionScreen(
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
        Exit code (0 for success).
    """
    app = D3ployTUI(config_path=config_path)
    result = app.run()

    # Handle exit messages
    if result and isinstance(result, str):
        print(result)

    return 0
