"""Tests for clipboard and sound utilities."""

from unittest.mock import MagicMock, patch

import pyperclip

from src.clipboard import copy_and_notify


class TestCopyAndNotify:
    """Tests for the copy_and_notify function."""

    @patch("src.clipboard.pyperclip.copy")
    def test_copies_text_to_clipboard(self, mock_copy):
        """Verify text is placed on the clipboard."""
        result = copy_and_notify("test text", sound_effect=None)
        mock_copy.assert_called_once_with("test text")
        assert result is True

    @patch("src.clipboard.pyperclip.copy")
    def test_copies_empty_string(self, mock_copy):
        """Verify empty string can be copied."""
        result = copy_and_notify("", sound_effect=None)
        mock_copy.assert_called_once_with("")
        assert result is True

    @patch(
        "src.clipboard.pyperclip.copy",
        side_effect=pyperclip.PyperclipException("no clipboard"),
    )
    def test_copy_failure_returns_false(self, mock_copy):
        """Clipboard errors must not raise."""
        result = copy_and_notify("test text", sound_effect=None)
        assert result is False
        mock_copy.assert_called_once_with("test text")

    @patch("src.clipboard.pyperclip.copy")
    def test_plays_provided_sound_effect(self, mock_copy):
        """A preloaded sound effect is played after a successful copy."""
        effect = MagicMock()
        assert copy_and_notify("ok", sound_effect=effect) is True
        effect.play.assert_called_once()
