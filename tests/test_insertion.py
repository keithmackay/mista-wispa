# tests/test_insertion.py
from unittest.mock import patch, MagicMock, call

from mista_wispa.insertion import insert_text, _insert_via_accessibility, _insert_via_clipboard


def test_insert_via_clipboard_sets_and_restores():
    with patch("mista_wispa.insertion._get_pasteboard") as mock_pb_fn:
        mock_pb = MagicMock()
        mock_pb_fn.return_value = mock_pb
        # Simulate existing clipboard content
        mock_pb.stringForType_.return_value = "old clipboard"
        with patch("mista_wispa.insertion._simulate_paste") as mock_paste:
            with patch("mista_wispa.insertion.time.sleep"):
                _insert_via_clipboard("new text")
        # Should have set "new text" on pasteboard
        mock_pb.clearContents.assert_called()
        mock_pb.setString_forType_.assert_any_call("new text", "public.utf8-plain-text")


def test_insert_text_tries_accessibility_first():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=True) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_not_called()
    assert result is True


def test_insert_text_falls_back_to_clipboard():
    with patch("mista_wispa.insertion._insert_via_accessibility", return_value=False) as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("hello")
    mock_ax.assert_called_once_with("hello")
    mock_clip.assert_called_once_with("hello")
    assert result is True


def test_insert_text_empty_string_is_noop():
    with patch("mista_wispa.insertion._insert_via_accessibility") as mock_ax:
        with patch("mista_wispa.insertion._insert_via_clipboard") as mock_clip:
            result = insert_text("")
    mock_ax.assert_not_called()
    mock_clip.assert_not_called()
    assert result is False
