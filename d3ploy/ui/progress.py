"""
Progress display components.
"""

from typing import Optional

from rich.console import Console
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskProgressColumn
from rich.progress import TextColumn
from rich.progress import TimeElapsedColumn


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
