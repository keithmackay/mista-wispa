# tests/test_notify.py
from unittest.mock import patch

from mista_wispa.notify import notify


def test_notify_calls_rumps_notification():
    with patch("mista_wispa.notify.rumps.notification") as mock_notif:
        notify("Title", "Body text")
    mock_notif.assert_called_once_with(
        title="Title",
        subtitle="",
        message="Body text",
        sound=False,
    )


def test_notify_with_subtitle():
    with patch("mista_wispa.notify.rumps.notification") as mock_notif:
        notify("Title", "Body", subtitle="Sub")
    mock_notif.assert_called_once_with(
        title="Title",
        subtitle="Sub",
        message="Body",
        sound=False,
    )
