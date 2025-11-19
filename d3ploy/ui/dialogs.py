"""
Interactive dialogs using Rich prompts.
"""

from rich.prompt import Confirm
from rich.prompt import Prompt


def confirm_delete(file: str) -> bool:
    """
    Ask user to confirm file deletion.

    Args:
        file: File path to delete.

    Returns:
        True if user confirms deletion.
    """
    return Confirm.ask(f"Remove {file}?", default=False)


def show_dialog(
    title: str,
    message: str,
    choices: list[str],
    *,
    default: str | None = None,
) -> str:
    """
    Show dialog with custom choices.

    Args:
        title: Dialog title.
        message: Dialog message.
        choices: List of choice labels.
        default: Default choice.

    Returns:
        Choice selected by user.
    """
    prompt_text = f"[bold]{title}[/bold]\n{message}"
    result = Prompt.ask(
        prompt_text,
        choices=choices,
        default=default,
    )
    # When choices are provided, Prompt.ask will always return a string (reprompts if invalid)
    assert result is not None
    return result
