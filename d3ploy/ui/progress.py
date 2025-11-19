"""
Progress display components.
"""

from typing import Dict
from typing import List
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskID
from rich.progress import TaskProgressColumn
from rich.progress import TextColumn
from rich.progress import TimeElapsedColumn
from rich.table import Table


class ProgressDisplay:
    """
    Progress display using Rich library (part of Textual ecosystem).

    Replaces tqdm with Rich-based progress bars that work both in
    terminal and Textual applications.
    """

    def __init__(
        self,
        total: Optional[int] = None,
        *,
        description: str = "",
        disable: bool = False,
        colour: str = "green",
        unit: str = "items",
    ):
        """
        Initialize progress display.

        Args:
            total: Total number of items to process.
            description: Progress bar description.
            disable: If True, disable progress display.
            colour: Progress bar color.
            unit: Unit name for items.
        """
        self.disable = disable
        self.console = Console()

        if not disable:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn(unit),
                TimeElapsedColumn(),
                console=self.console,
            )
            self.task_id = None
            self.total = total
            self.description = description
            self._started = False

    def __enter__(self):
        """Context manager entry."""
        if not self.disable:
            self.progress.__enter__()
            self.task_id = self.progress.add_task(
                self.description,
                total=self.total,
            )
            self._started = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self.disable and self._started:
            self.progress.__exit__(exc_type, exc_val, exc_tb)

    def update(self, n: int = 1):
        """
        Update progress by n steps.

        Args:
            n: Number of steps to advance.
        """
        if not self.disable and self._started and self.task_id is not None:
            self.progress.update(self.task_id, advance=n)

    def set_description(self, desc: str):
        """
        Set progress description text.

        Args:
            desc: New description.
        """
        if not self.disable and self._started and self.task_id is not None:
            self.progress.update(self.task_id, description=desc)


class LiveProgressDisplay:
    """
    Live progress display with real-time file operations tracking.

    Uses Rich Live display to show progress bars alongside a table
    of recently processed files and current operations.
    """

    def __init__(
        self,
        *,
        title: str = "Sync Progress",
        disable: bool = False,
    ):
        """
        Initialize live progress display.

        Args:
            title: Title for the display.
            disable: If True, disable live display.
        """
        self.disable = disable
        self.console = Console()
        self.title = title

        if not disable:
            # Create progress bar
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
            )

            # Track tasks
            self.tasks: Dict[str, TaskID] = {}

            # Track recent file operations
            self.recent_files: List[Dict[str, str]] = []
            self.max_recent = 10

            # Create layout
            self.layout = Layout()
            self.layout.split_column(
                Layout(name="progress", size=None),
                Layout(name="files", size=12),
            )

            # Live display
            self.live = Live(
                self.layout,
                console=self.console,
                refresh_per_second=4,
            )
            self._started = False

    def __enter__(self):
        """Context manager entry."""
        if not self.disable:
            self.live.__enter__()
            self._started = True
            self._update_display()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self.disable and self._started:
            self.live.__exit__(exc_type, exc_val, exc_tb)

    def add_task(
        self,
        name: str,
        *,
        description: str,
        total: Optional[int] = None,
    ) -> str:
        """
        Add a new progress task.

        Args:
            name: Task identifier.
            description: Task description.
            total: Total steps for the task.

        Returns:
            Task identifier.
        """
        if not self.disable:
            task_id = self.progress.add_task(description, total=total)
            self.tasks[name] = task_id
            self._update_display()
        return name

    def update_task(
        self,
        name: str,
        *,
        advance: int = 1,
        description: Optional[str] = None,
    ):
        """
        Update a task's progress.

        Args:
            name: Task identifier.
            advance: Number of steps to advance.
            description: New description (optional).
        """
        if not self.disable and name in self.tasks:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.tasks[name], **kwargs)
            self._update_display()

    def add_file_operation(
        self,
        *,
        file: str,
        operation: str,
        status: str = "✓",
    ):
        """
        Add a file operation to the recent files list.

        Args:
            file: File path/name.
            operation: Operation performed (upload, delete, etc.).
            status: Status indicator.
        """
        if not self.disable:
            self.recent_files.insert(
                0,
                {"file": file, "operation": operation, "status": status},
            )
            # Keep only recent files
            self.recent_files = self.recent_files[: self.max_recent]
            self._update_display()

    def _update_display(self):
        """Update the live display with current progress and files."""
        if not self.disable and self._started:
            # Update progress section
            self.layout["progress"].update(
                Panel(
                    self.progress,
                    title=self.title,
                    border_style="blue",
                )
            )

            # Update files section
            if self.recent_files:
                table = Table(
                    show_header=True,
                    header_style="bold cyan",
                    title="Recent Operations",
                    title_style="bold white",
                )
                table.add_column("Status", width=6, style="green")
                table.add_column("Operation", width=10)
                table.add_column("File", style="dim")

                for op in self.recent_files:
                    table.add_row(
                        op["status"],
                        op["operation"],
                        op["file"],
                    )

                self.layout["files"].update(table)
            else:
                self.layout["files"].update(
                    Panel(
                        "[dim]No operations yet[/dim]",
                        border_style="dim",
                    )
                )
