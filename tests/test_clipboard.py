"""Tests for clipboard and sound utilities."""

from unittest.mock import patch

from src.clipboard import copy_and_notify


class TestCopyAndNotify:
    """Tests for the copy_and_notify function."""

    @patch("src.clipboard.pyperclip.copy")
    def test_copies_text_to_clipboard(self, mock_copy):
        """Verify text is placed on the clipboard."""
        copy_and_notify("test text", sound_effect=None)
        mock_copy.assert_called_once_with("test text")

    @patch("src.clipboard.pyperclip.copy")
    def test_copies_empty_string(self, mock_copy):
        """Verify empty string can be copied."""
        copy_and_notify("", sound_effect=None)
        mock_copy.assert_called_once_with("")
