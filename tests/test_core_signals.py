"""
Tests for d3ploy.core.signals module.
"""

import signal
from unittest.mock import patch

import pytest

from d3ploy.core import signals
from d3ploy.sync import operations


@pytest.fixture
def reset_killswitch():
    """Reset killswitch before and after each test."""
    operations.killswitch.clear()
    yield
    operations.killswitch.clear()


# Tests for UserCancelled exception


def test_user_cancelled_is_exception():
    """UserCancelled is an Exception."""
    assert issubclass(signals.UserCancelled, Exception)


def test_user_cancelled_with_message():
    """UserCancelled can be raised with message."""
    with pytest.raises(signals.UserCancelled) as exc_info:
        raise signals.UserCancelled("Test message")

    assert str(exc_info.value) == "Test message"


# Tests for bail


def test_bail_sets_killswitch(reset_killswitch):
    """bail() sets the killswitch."""
    with pytest.raises(signals.UserCancelled):
        signals.bail()

    assert operations.killswitch.is_set()


def test_bail_raises_user_cancelled(reset_killswitch):
    """bail() raises UserCancelled."""
    with pytest.raises(signals.UserCancelled) as exc_info:
        signals.bail()

    assert "cancelled by user" in str(exc_info.value).lower()


def test_bail_with_signal_args(reset_killswitch):
    """bail() handles signal arguments."""
    with pytest.raises(signals.UserCancelled):
        signals.bail(signal.SIGINT, None)

    assert operations.killswitch.is_set()


def test_bail_with_kwargs(reset_killswitch):
    """bail() handles keyword arguments."""
    with pytest.raises(signals.UserCancelled):
        signals.bail(custom_arg="value")

    assert operations.killswitch.is_set()


# Tests for setup_signal_handlers


def test_setup_signal_handlers_registers_sigint():
    """setup_signal_handlers() registers SIGINT handler."""
    with patch("signal.signal") as mock_signal:
        signals.setup_signal_handlers()

        mock_signal.assert_called_once_with(signal.SIGINT, signals.bail)


def test_setup_signal_handlers_can_be_called_multiple_times():
    """setup_signal_handlers() can be called multiple times safely."""
    with patch("signal.signal") as mock_signal:
        signals.setup_signal_handlers()
        signals.setup_signal_handlers()

        assert mock_signal.call_count == 2


# Tests for shutdown_requested


def test_shutdown_requested_false_initially(reset_killswitch):
    """shutdown_requested() returns False initially."""
    assert signals.shutdown_requested() is False


def test_shutdown_requested_true_after_bail(reset_killswitch):
    """shutdown_requested() returns True after bail() called."""
    try:
        signals.bail()
    except signals.UserCancelled:
        pass

    assert signals.shutdown_requested() is True


def test_shutdown_requested_true_when_killswitch_set(reset_killswitch):
    """shutdown_requested() returns True when killswitch is set."""
    operations.killswitch.set()

    assert signals.shutdown_requested() is True


def test_shutdown_requested_false_after_clear(reset_killswitch):
    """shutdown_requested() returns False after killswitch cleared."""
    operations.killswitch.set()
    operations.killswitch.clear()

    assert signals.shutdown_requested() is False
