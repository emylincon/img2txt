"""Preview window showing image and extracted text."""

from __future__ import annotations

import platform
from typing import Literal

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.clipboard import copy_and_notify

# Same threshold as SelectionOverlay: ignore tiny drags.
_MIN_SELECTION_PX = 10
_HANDLE_SIZE = 8
_HANDLE_HIT = 12

HandleName = Literal["tl", "tr", "bl", "br"]


def _monospace_font_family() -> str:
    """Return a platform-appropriate monospace font family."""
    system = platform.system()
    if system == "Darwin":
        return "Menlo"
    if system == "Windows":
        return "Consolas"
    return "Monospace"


def displayed_pixmap_rect(
    widget_size: QSize,
    image_size: QSize,
) -> QRect:
    """Return the letterboxed dest rect of a KeepAspectRatio pixmap.

    The image is scaled to fit *widget_size* while preserving
    aspect ratio and centered, matching ``QLabel`` +
    ``AlignCenter`` behaviour.
    """
    if (
        widget_size.width() <= 0
        or widget_size.height() <= 0
        or image_size.width() <= 0
        or image_size.height() <= 0
    ):
        return QRect()

    scaled = image_size.scaled(
        widget_size,
        Qt.AspectRatioMode.KeepAspectRatio,
    )
    x = (widget_size.width() - scaled.width()) // 2
    y = (widget_size.height() - scaled.height()) // 2
    return QRect(x, y, scaled.width(), scaled.height())


def widget_to_image_rect(
    widget_rect: QRect,
    widget_size: QSize,
    image_size: QSize,
) -> QRect | None:
    """Map a widget-space rect onto original image pixels.

    Returns ``None`` if the dest pixmap has no area or the
    mapped rect is smaller than ``_MIN_SELECTION_PX``.
    """
    dest = displayed_pixmap_rect(widget_size, image_size)
    if dest.width() <= 0 or dest.height() <= 0:
        return None

    clipped = widget_rect.normalized().intersected(dest)
    if clipped.width() <= 0 or clipped.height() <= 0:
        return None

    scale_x = image_size.width() / dest.width()
    scale_y = image_size.height() / dest.height()

    x1 = round((clipped.x() - dest.x()) * scale_x)
    y1 = round((clipped.y() - dest.y()) * scale_y)
    x2 = round((clipped.x() + clipped.width() - dest.x()) * scale_x)
    y2 = round((clipped.y() + clipped.height() - dest.y()) * scale_y)

    x1 = max(0, min(x1, image_size.width()))
    y1 = max(0, min(y1, image_size.height()))
    x2 = max(0, min(x2, image_size.width()))
    y2 = max(0, min(y2, image_size.height()))

    mapped = QRect(x1, y1, x2 - x1, y2 - y1).normalized()
    if (
        mapped.width() < _MIN_SELECTION_PX
        or mapped.height() < _MIN_SELECTION_PX
    ):
        return None
    return mapped


def image_to_widget_rect(
    image_rect: QRect,
    widget_size: QSize,
    image_size: QSize,
) -> QRect:
    """Map an original-image rect onto widget space."""
    dest = displayed_pixmap_rect(widget_size, image_size)
    if dest.width() <= 0 or dest.height() <= 0:
        return QRect()

    scale_x = dest.width() / image_size.width()
    scale_y = dest.height() / image_size.height()
    x = dest.x() + round(image_rect.x() * scale_x)
    y = dest.y() + round(image_rect.y() * scale_y)
    w = round(image_rect.width() * scale_x)
    h = round(image_rect.height() * scale_y)
    return QRect(x, y, w, h)


def _handle_rects(selection: QRect) -> dict[HandleName, QRect]:
    """Return corner handle rects in widget space."""
    half = _HANDLE_SIZE // 2
    corners: dict[HandleName, QPoint] = {
        "tl": selection.topLeft(),
        "tr": selection.topRight(),
        "bl": selection.bottomLeft(),
        "br": selection.bottomRight(),
    }
    return {
        name: QRect(
            point.x() - half,
            point.y() - half,
            _HANDLE_SIZE,
            _HANDLE_SIZE,
        )
        for name, point in corners.items()
    }


class ImageLabel(QLabel):
    """A label that scales its pixmap and supports region selection.

    Signals:
        region_selected(QRect): Original-image pixel crop.
        selection_cleared(): Selection was reset to the full image.
    """

    region_selected = pyqtSignal(QRect)
    selection_cleared = pyqtSignal()

    _BORDER_COLOR = QColor(255, 255, 255, 220)
    _BORDER_WIDTH = 2
    _HANDLE_FILL = QColor(255, 255, 255, 240)
    _HANDLE_BORDER = QColor(30, 30, 30, 220)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setMouseTracking(True)
        self._pixmap: QPixmap | None = None
        self._selection: QRect | None = None
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._active_handle: HandleName | None = None

    def set_image(self, pixmap: QPixmap) -> None:
        """Set and display a scaled pixmap, clearing any selection."""
        self._pixmap = pixmap
        self._selection = None
        self._origin = None
        self._current = None
        self._active_handle = None
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self._update_scaled()
        self.update()

    def clear_selection(self) -> None:
        """Reset to the full image and emit ``selection_cleared``."""
        if (
            self._selection is None
            and self._origin is None
            and self._current is None
        ):
            return
        self._selection = None
        self._origin = None
        self._current = None
        self._active_handle = None
        self.update()
        self.selection_cleared.emit()

    def has_selection(self) -> bool:
        """Return True when a crop region is active."""
        return self._selection is not None

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        """Rescale pixmap on resize."""
        super().resizeEvent(event)
        self._update_scaled()

    def _update_scaled(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def _image_size(self) -> QSize | None:
        if self._pixmap is None or self._pixmap.isNull():
            return None
        return self._pixmap.size()

    def _hit_handle(self, pos: QPoint) -> HandleName | None:
        if self._selection is None:
            return None
        image_size = self._image_size()
        if image_size is None:
            return None
        widget_sel = image_to_widget_rect(
            self._selection,
            self.size(),
            image_size,
        )
        half = _HANDLE_HIT // 2
        for name, rect in _handle_rects(widget_sel).items():
            hit = rect.adjusted(-half, -half, half, half)
            if hit.contains(pos):
                return name
        return None

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """Draw the scaled pixmap plus selection overlay."""
        super().paintEvent(event)
        selection = self._widget_selection()
        if selection is None:
            return

        painter = QPainter(self)
        pen = QPen(self._BORDER_COLOR, self._BORDER_WIDTH)
        painter.setPen(pen)
        painter.drawRect(selection)

        if self._origin is None:
            painter.setBrush(self._HANDLE_FILL)
            painter.setPen(QPen(self._HANDLE_BORDER, 1))
            for rect in _handle_rects(selection).values():
                painter.drawRect(rect)
        painter.end()

    def _widget_selection(self) -> QRect | None:
        if self._origin is not None and self._current is not None:
            return QRect(self._origin, self._current).normalized()
        if self._selection is None:
            return None
        image_size = self._image_size()
        if image_size is None:
            return None
        return image_to_widget_rect(
            self._selection,
            self.size(),
            image_size,
        )

    def mousePressEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Start a drag or handle resize."""
        if event.button() != Qt.MouseButton.LeftButton or self._pixmap is None:
            return

        handle = self._hit_handle(event.pos())
        if handle is not None and self._selection is not None:
            image_size = self._image_size()
            if image_size is None:
                return
            widget_sel = image_to_widget_rect(
                self._selection,
                self.size(),
                image_size,
            )
            opposite = {
                "tl": widget_sel.bottomRight(),
                "tr": widget_sel.bottomLeft(),
                "bl": widget_sel.topRight(),
                "br": widget_sel.topLeft(),
            }[handle]
            self._active_handle = handle
            self._origin = opposite
            self._current = event.pos()
            self.update()
            return

        self._active_handle = None
        self._origin = event.pos()
        self._current = event.pos()
        self.update()

    def mouseMoveEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Update the rubber band or hover cursor."""
        if self._origin is not None:
            self._current = event.pos()
            self.update()
            return

        if self._pixmap is None:
            self.unsetCursor()
            return

        handle = self._hit_handle(event.pos())
        if handle in ("tl", "br"):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif handle in ("tr", "bl"):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def mouseReleaseEvent(  # noqa: N802
        self, event: QMouseEvent
    ) -> None:
        """Commit a selection in original-image pixels."""
        if (
            event.button() != Qt.MouseButton.LeftButton
            or self._origin is None
            or self._current is None
        ):
            return

        widget_rect = QRect(self._origin, self._current).normalized()
        self._origin = None
        self._current = None
        self._active_handle = None

        image_size = self._image_size()
        if image_size is None:
            self.update()
            return

        mapped = widget_to_image_rect(
            widget_rect,
            self.size(),
            image_size,
        )
        if mapped is None:
            # Keep the previous selection if a tiny drag
            # happened while resizing; otherwise ignore.
            self.update()
            return

        self._selection = mapped
        self.update()
        self.region_selected.emit(mapped)

    def keyPressEvent(  # noqa: N802
        self, event: QKeyEvent
    ) -> None:
        """Clear the selection on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.clear_selection()
        else:
            super().keyPressEvent(event)


class PreviewWidget(QWidget):
    """Side-by-side image and text preview."""

    region_selected = pyqtSignal(QRect)
    selection_cleared = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: image + clear-selection control
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = ImageLabel()
        self.image_label.setText("No image loaded")
        self.image_label.region_selected.connect(self._on_region_selected)
        self.image_label.selection_cleared.connect(self._on_selection_cleared)
        left_layout.addWidget(self.image_label)

        self.clear_selection_btn = QPushButton("Clear selection")
        self.clear_selection_btn.setEnabled(False)
        self.clear_selection_btn.clicked.connect(
            self.image_label.clear_selection
        )
        left_layout.addWidget(self.clear_selection_btn)

        self.splitter.addWidget(left)

        # Right panel: text + copy button
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Extracted text will appear here. You can edit before copying…"
        )
        self._default_font = self.text_edit.font()
        self.text_edit.textChanged.connect(self._on_text_changed)
        right_layout.addWidget(self.text_edit)

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._on_copy)
        right_layout.addWidget(self.copy_btn)

        self.splitter.addWidget(right)
        self.splitter.setSizes([400, 400])

        layout.addWidget(self.splitter)

    def set_image(self, pixmap: QPixmap) -> None:
        """Display an image in the left panel."""
        self.image_label.set_image(pixmap)
        self.clear_selection_btn.setEnabled(False)

    def set_text(self, text: str) -> None:
        """Display extracted text in the right panel."""
        self.text_edit.setPlainText(text)
        self.copy_btn.setEnabled(bool(text))

    def set_monospace(self, enabled: bool) -> None:
        """Toggle monospace font and word wrap for layout mode.

        Args:
            enabled: When True, use a monospace font and
                disable word wrap to preserve alignment.
                When False, restore the default font and
                word wrap.
        """
        if enabled:
            font = QFont(_monospace_font_family())
            self.text_edit.setFont(font)
            self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        else:
            self.text_edit.setFont(self._default_font)
            self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

    def _on_region_selected(self, rect: QRect) -> None:
        self.clear_selection_btn.setEnabled(True)
        self.region_selected.emit(rect)

    def _on_selection_cleared(self) -> None:
        self.clear_selection_btn.setEnabled(False)
        self.selection_cleared.emit()

    def _on_text_changed(self) -> None:
        self.copy_btn.setEnabled(bool(self.text_edit.toPlainText()))

    def _on_copy(self) -> None:
        text = self.text_edit.toPlainText()
        if not text:
            return
        if not copy_and_notify(text):
            QMessageBox.warning(
                self,
                "Clipboard Error",
                "Could not copy text to the clipboard.",
            )
