"""Fullscreen overlay for selecting a screen region."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QRegion,
)
from PyQt6.QtWidgets import QWidget


class SelectionOverlay(QWidget):
    """Translucent fullscreen overlay for region selection.

    Displays the screenshot dimmed and lets the user drag
    a rectangle to select a region.

    Signals:
        region_selected(QRect): Emitted with the selected
            rectangle when the user releases the mouse.
        cancelled(): Emitted when the user presses Escape.
    """

    region_selected = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    _OVERLAY_COLOR = QColor(0, 0, 0, 120)
    _BORDER_COLOR = QColor(255, 255, 255, 200)
    _BORDER_WIDTH = 2

    def __init__(
        self,
        screenshot: QPixmap,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._screenshot = screenshot
        self._origin: QPoint | None = None
        self._current: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMouseTracking(True)

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """Draw the screenshot with a dark overlay."""
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._screenshot)

        # Draw dark wash over entire area
        if self._origin and self._current:
            selection = QRect(self._origin, self._current).normalized()

            # Dark overlay with hole for selection
            full = QRegion(self.rect())
            hole = QRegion(selection)
            dark = full.subtracted(hole)

            painter.setClipRegion(dark)
            painter.fillRect(self.rect(), self._OVERLAY_COLOR)
            painter.setClipping(False)

            # Border around selection
            pen = QPen(self._BORDER_COLOR, self._BORDER_WIDTH)
            painter.setPen(pen)
            painter.drawRect(selection)
        else:
            painter.fillRect(self.rect(), self._OVERLAY_COLOR)

        painter.end()

    def mousePressEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Record the start point of the selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self.update()

    def mouseMoveEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Update the selection rectangle."""
        if self._origin is not None:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Emit the selected region."""
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._origin is not None
            and self._current is not None
        ):
            rect = QRect(self._origin, self._current).normalized()
            self.close()

            if rect.width() > 2 and rect.height() > 2:
                self.region_selected.emit(rect)
            else:
                self.cancelled.emit()

            self._origin = None
            self._current = None

    def keyPressEvent(  # noqa: N802
        self, event: QKeyEvent
    ) -> None:
        """Cancel on Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)
