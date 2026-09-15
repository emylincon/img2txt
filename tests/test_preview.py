"""Tests for the preview widget."""

from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication

from src.preview import PreviewWidget


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestPreviewWidgetEditable:
    """Tests for editable text in the preview box."""

    def test_text_edit_is_not_read_only(self, qapp):
        """QTextEdit should be editable (not read-only)."""
        widget = PreviewWidget()
        assert widget.text_edit.isReadOnly() is False

    def test_set_text_populates_and_enables_copy(self, qapp):
        """set_text should populate the text area and enable copy."""
        widget = PreviewWidget()
        widget.set_text("hello world")
        assert widget.text_edit.toPlainText() == "hello world"
        assert widget.copy_btn.isEnabled() is True

    def test_set_text_empty_disables_copy(self, qapp):
        """set_text with empty string should disable copy button."""
        widget = PreviewWidget()
        widget.set_text("some text")
        widget.set_text("")
        assert widget.copy_btn.isEnabled() is False

    def test_user_edit_updates_plain_text(self, qapp):
        """Typing into the QTextEdit changes toPlainText."""
        widget = PreviewWidget()
        widget.text_edit.setPlainText("original")
        widget.text_edit.setPlainText("edited by user")
        assert widget.text_edit.toPlainText() == "edited by user"

    def test_copy_button_disabled_when_user_clears_text(self, qapp):
        """Copy button should disable when user clears all text."""
        widget = PreviewWidget()
        widget.set_text("some text")
        assert widget.copy_btn.isEnabled() is True
        widget.text_edit.setPlainText("")
        assert widget.copy_btn.isEnabled() is False

    def test_copy_button_enabled_when_user_types_text(self, qapp):
        """Copy button should enable when user types into empty box."""
        widget = PreviewWidget()
        assert widget.copy_btn.isEnabled() is False
        widget.text_edit.setPlainText("user typed this")
        assert widget.copy_btn.isEnabled() is True

    @patch("src.preview.copy_and_notify")
    def test_copy_uses_edited_text(self, mock_copy, qapp):
        """Copy should use the current (edited) text, not original."""
        widget = PreviewWidget()
        widget.set_text("original ocr text")
        widget.text_edit.setPlainText("corrected text")
        widget._on_copy()
        mock_copy.assert_called_once_with("corrected text")

    def test_placeholder_mentions_editing(self, qapp):
        """Placeholder text should hint that editing is possible."""
        widget = PreviewWidget()
        placeholder = widget.text_edit.placeholderText()
        assert "edit" in placeholder.lower()
