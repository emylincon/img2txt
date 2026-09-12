"""Preview window showing image and extracted text."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.clipboard import copy_and_notify


class ImageLabel(QLabel):
    """A label that scales its pixmap to fit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self._pixmap: QPixmap | None = None

    def set_image(self, pixmap: QPixmap) -> None:
        """Set and display a scaled pixmap."""
        self._pixmap = pixmap
        self._update_scaled()

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


class PreviewWidget(QWidget):
    """Side-by-side image and text preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: image
        self.image_label = ImageLabel()
        self.image_label.setText("No image loaded")
        self.splitter.addWidget(self.image_label)

        # Right panel: text + copy button
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText("Extracted text will appear here…")
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

    def set_text(self, text: str) -> None:
        """Display extracted text in the right panel."""
        self.text_edit.setPlainText(text)
        self.copy_btn.setEnabled(bool(text))

    def _on_copy(self) -> None:
        text = self.text_edit.toPlainText()
        if text:
            copy_and_notify(text)
