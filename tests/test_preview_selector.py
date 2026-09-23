"""Tests for the preview-panel region selector."""

from unittest.mock import patch

import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication

from src.preview import (
    ImageLabel,
    displayed_pixmap_rect,
    widget_to_image_rect,
)


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    return QApplication.instance() or QApplication([])


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


class TestCoordinateMapping:
    """Map widget drags onto original-image pixels."""

    def test_letterboxed_drag_maps_to_image_pixels(self):
        """A known widget drag produces the expected image QRect."""
        widget = QSize(200, 100)
        image = QSize(100, 100)
        dest = displayed_pixmap_rect(widget, image)
        assert dest == QRect(50, 0, 100, 100)

        mapped = widget_to_image_rect(
            QRect(60, 10, 80, 80),
            widget,
            image,
        )
        assert mapped == QRect(10, 10, 80, 80)

    def test_identity_mapping_when_sizes_match(self):
        """No letterbox: widget coords equal image coords."""
        size = QSize(200, 200)
        mapped = widget_to_image_rect(QRect(20, 30, 40, 50), size, size)
        assert mapped == QRect(20, 30, 40, 50)

    def test_tiny_selection_is_ignored(self):
        """Selections smaller than 10×10 px return None."""
        size = QSize(200, 200)
        assert widget_to_image_rect(QRect(10, 10, 5, 5), size, size) is None
        assert widget_to_image_rect(QRect(10, 10, 20, 5), size, size) is None


class TestImageLabelSelection:
    """Widget-level rubber-band behaviour."""

    def test_clear_selection_emits(self, qapp):
        """clear_selection emits selection_cleared after a crop."""
        label = ImageLabel()
        label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("red"))
        label.set_image(pixmap)

        cleared: list[bool] = []
        label.selection_cleared.connect(lambda: cleared.append(True))

        label._selection = QRect(10, 10, 40, 40)
        label.clear_selection()
        assert cleared == [True]
        assert label.has_selection() is False

    def test_escape_clears_selection(self, qapp):
        """Escape resets the crop and emits selection_cleared."""
        label = ImageLabel()
        label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("red"))
        label.set_image(pixmap)
        label._selection = QRect(10, 10, 40, 40)

        cleared: list[bool] = []
        label.selection_cleared.connect(lambda: cleared.append(True))
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
        )
        label.keyPressEvent(event)
        assert cleared == [True]

    def test_tiny_drag_does_not_emit_region(self, qapp):
        """A sub-threshold mouse drag is ignored."""
        label = ImageLabel()
        label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("blue"))
        label.set_image(pixmap)

        selected: list[QRect] = []
        label.region_selected.connect(selected.append)

        label.mousePressEvent(
            _mouse(QEvent.Type.MouseButtonPress, QPoint(20, 20))
        )
        label.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, QPoint(24, 24)))
        label.mouseReleaseEvent(
            _mouse(QEvent.Type.MouseButtonRelease, QPoint(24, 24))
        )
        assert selected == []
        assert label.has_selection() is False

    def test_drag_emits_original_image_rect(self, qapp):
        """A large enough drag maps 1:1 when widget and image match."""
        label = ImageLabel()
        label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("blue"))
        label.set_image(pixmap)

        selected: list[QRect] = []
        label.region_selected.connect(selected.append)

        label.mousePressEvent(
            _mouse(QEvent.Type.MouseButtonPress, QPoint(20, 30))
        )
        label.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, QPoint(80, 90)))
        label.mouseReleaseEvent(
            _mouse(QEvent.Type.MouseButtonRelease, QPoint(80, 90))
        )
        assert selected == [QRect(20, 30, 61, 61)]

    def test_press_grabs_mouse_and_release_ungrabs(self, qapp):
        """Drags grab the mouse so a release outside still commits."""
        label = ImageLabel()
        label.resize(200, 200)
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor("blue"))
        label.set_image(pixmap)
        with (
            patch.object(label, "grabMouse") as mock_grab,
            patch.object(label, "releaseMouse") as mock_release,
            patch.object(label, "mouseGrabber", return_value=label),
        ):
            label.mousePressEvent(
                _mouse(QEvent.Type.MouseButtonPress, QPoint(20, 30))
            )
            mock_grab.assert_called_once()
            label.mouseReleaseEvent(
                _mouse(QEvent.Type.MouseButtonRelease, QPoint(80, 90))
            )
            mock_release.assert_called_once()
