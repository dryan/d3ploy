"""
Progress display components.
"""


class ProgressDisplay:
    """
    Custom progress display widget.

    Replaces tqdm with Textual-based progress bars.
    """

    def __init__(self, total: int, description: str = ""):
        # TODO: Implement in Phase 3.4
        raise NotImplementedError("Progress display will be implemented in Phase 3.4")

    def update(self, n: int = 1):
        """
        Update progress by n steps.

        Args:
            n: Number of steps to advance.
        """
        # TODO: Implement in Phase 3.4
        raise NotImplementedError("Progress update will be implemented in Phase 3.4")

    def set_description(self, desc: str):
        """
        Set progress description text.

        Args:
            desc: New description.
        """
        # TODO: Implement in Phase 3.4
        raise NotImplementedError(
            "Progress description will be implemented in Phase 3.4"
        )
