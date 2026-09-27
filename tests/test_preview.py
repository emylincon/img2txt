"""Tests for the preview widget."""

from unittest.mock import patch

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.preview import PreviewWidget


def _mouse(
    event_type: QEvent.Type,
    pos: QPoint,
    *,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> QMouseEvent:
    buttons = (
        Qt.MouseButton.NoButton
        if event_type == QEvent.Type.MouseButtonRelease
        else button
    )
    return QMouseEvent(
        event_type,
        QPointF(pos),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


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

    @patch("src.preview.copy_and_notify", return_value=False)
    @patch.object(QMessageBox, "warning")
    def test_copy_failure_shows_warning(self, mock_warn, mock_copy, qapp):
        """A clipboard failure surfaces a warning dialog."""
        widget = PreviewWidget()
        widget.set_text("copied")
        widget._on_copy()
        mock_copy.assert_called_once_with("copied")
        mock_warn.assert_called_once()


class TestPreviewSelector:
    """Preview panel region-selection wiring."""

    def test_region_selected_enables_clear_button(self, qapp):
        """A crop on the image label enables Clear selection."""
        widget = PreviewWidget()
        pixmap = QPixmap(80, 80)
        pixmap.fill(QColor("green"))
        widget.set_image(pixmap)
        assert widget.clear_selection_btn.isEnabled() is False

        received: list[QRect] = []
        widget.region_selected.connect(received.append)
        widget.image_label.region_selected.emit(QRect(5, 5, 20, 20))
        assert received == [QRect(5, 5, 20, 20)]
        assert widget.clear_selection_btn.isEnabled() is True

    def test_clear_button_resets_selection(self, qapp):
        """Clear selection emits selection_cleared and disables itself."""
        widget = PreviewWidget()
        pixmap = QPixmap(80, 80)
        pixmap.fill(QColor("green"))
        widget.set_image(pixmap)
        widget.image_label._selection = QRect(5, 5, 20, 20)
        widget.clear_selection_btn.setEnabled(True)

        cleared: list[bool] = []
        widget.selection_cleared.connect(lambda: cleared.append(True))
        widget.clear_selection_btn.click()
        assert cleared == [True]
        assert widget.clear_selection_btn.isEnabled() is False
        assert widget.image_label.has_selection() is False

    def test_clear_button_accepts_clicked_bool(self, qapp):
        """clicked(bool) must not TypeError the clear-selection slot."""
        widget = PreviewWidget()
        pixmap = QPixmap(80, 80)
        pixmap.fill(QColor("green"))
        widget.set_image(pixmap)
        widget.image_label._selection = QRect(5, 5, 20, 20)
        widget.clear_selection_btn.setEnabled(True)

        widget._on_clear_selection_clicked(True)
        assert widget.image_label.has_selection() is False
        assert widget.clear_selection_btn.isEnabled() is False

    def test_clear_button_after_mouse_drag(self, qapp):
        """A real crop then a button click restores the full image."""
        widget = PreviewWidget()
        widget.image_label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("green"))
        widget.set_image(pixmap)

        cleared: list[bool] = []
        widget.selection_cleared.connect(lambda: cleared.append(True))

        label = widget.image_label
        label.mousePressEvent(
            _mouse(QEvent.Type.MouseButtonPress, QPoint(20, 30))
        )
        label.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, QPoint(80, 90)))
        label.mouseReleaseEvent(
            _mouse(QEvent.Type.MouseButtonRelease, QPoint(80, 90))
        )
        assert widget.clear_selection_btn.isEnabled() is True
        assert label.has_selection() is True

        widget.clear_selection_btn.click()
        assert cleared == [True]
        assert widget.clear_selection_btn.isEnabled() is False
        assert label.has_selection() is False
        assert label._origin is None
        assert label._current is None
