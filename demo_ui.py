#!/usr/bin/env python3
"""Demo script to showcase the new Rich-based UI components."""

import time

from d3ploy.ui import dialogs
from d3ploy.ui import output
from d3ploy.ui import progress


def demo_output():
    """Demonstrate output formatting."""
    print("\n=== Output Demo ===\n")

    output.display_message("This is an informational message", level="info")
    output.display_message("This is a success message!", level="success")
    output.display_message("This is a warning message", level="warning")
    output.display_message("This is an error message", level="error")


def demo_progress():
    """Demonstrate progress bars."""
    print("\n=== Progress Bar Demo ===\n")

    with progress.ProgressDisplay(
        description="[green]Processing files...[/green]",
        total=100,
    ) as prog:
        for i in range(100):
            time.sleep(0.02)
            prog.update(1)

    output.display_message("Processing complete!", level="success")


def demo_dialogs():
    """Demonstrate interactive dialogs."""
    print("\n=== Dialog Demo ===\n")

    # Confirmation dialog
    result = dialogs.confirm_delete("example_file.txt")
    if result:
        output.display_message("User confirmed deletion", level="info")
    else:
        output.display_message("User cancelled deletion", level="warning")

    # Choice dialog
    choice = dialogs.show_dialog(
        title="Select Environment",
        message="Which environment would you like to deploy to?",
        choices=["development", "staging", "production"],
        default="development",
    )
    output.display_message(f"Selected environment: {choice}", level="success")


if __name__ == "__main__":
    output.display_message("d3ploy Rich UI Demo", level="success")
    output.display_message("=" * 50, level="info")

    demo_output()
    demo_progress()
    demo_dialogs()

    print("\n")
    output.display_message(
        "Demo complete! This is what your new UI looks like.", level="success"
    )
