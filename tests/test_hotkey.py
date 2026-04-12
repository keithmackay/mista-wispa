# tests/test_hotkey.py
from unittest.mock import MagicMock

from mista_wispa.hotkey import FnKeyMonitor


def test_initial_state():
    monitor = FnKeyMonitor(on_press=MagicMock(), on_release=MagicMock())
    assert monitor.is_pressed is False


def test_press_callback():
    on_press = MagicMock()
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=on_release)

    monitor._handle_fn_event(pressed=True)
    assert monitor.is_pressed is True
    on_press.assert_called_once()
    on_release.assert_not_called()


def test_release_callback():
    on_press = MagicMock()
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=on_release)

    monitor._handle_fn_event(pressed=True)
    monitor._handle_fn_event(pressed=False)
    assert monitor.is_pressed is False
    on_release.assert_called_once()


def test_duplicate_press_ignored():
    on_press = MagicMock()
    monitor = FnKeyMonitor(on_press=on_press, on_release=MagicMock())

    monitor._handle_fn_event(pressed=True)
    monitor._handle_fn_event(pressed=True)
    assert on_press.call_count == 1


def test_release_without_press_ignored():
    on_release = MagicMock()
    monitor = FnKeyMonitor(on_press=MagicMock(), on_release=on_release)

    monitor._handle_fn_event(pressed=False)
    on_release.assert_not_called()
