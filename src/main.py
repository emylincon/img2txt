"""IMG2TXT application entry point."""

from __future__ import annotations

import io
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QObject, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.capture import (
    ScreenRecordingPermissionError,
    crop_region,
    take_screenshot,
)
from src.ocr import (
    OCRError,
    TesseractMissingError,
    extract_text,
)
from src.picker import open_image_dialog
from src.preview import PreviewWidget
from src.selector import SelectionOverlay


class _OCRSignals(QObject):
    """Signals for OCR background task."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMG2TXT")
        self.setMinimumSize(800, 600)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._ocr_signals = _OCRSignals()
        self._ocr_signals.finished.connect(self._on_ocr_done)
        self._ocr_signals.error.connect(self._on_ocr_error)
        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        self.preview = PreviewWidget()
        layout.addWidget(self.preview)

        self.status_label = QLabel("")
        status_bar = QStatusBar()
        status_bar.addWidget(self.status_label)
        self.setStatusBar(status_bar)

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open Image…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_image)
        file_menu.addAction(open_action)

        capture_action = QAction("&Capture Screen", self)
        capture_action.setShortcut("Ctrl+Shift+X")
        capture_action.triggered.connect(self._capture_screen)
        file_menu.addAction(capture_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _open_image(self) -> None:
        path = open_image_dialog(self)
        if path is None:
            return
        self._load_image(path)

    def _load_image(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Could not find:\n{path}",
            )
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Invalid Image",
                f"Could not load image:\n{path}",
            )
            return

        self.preview.set_image(pixmap)
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")

        self._executor.submit(self._run_ocr, Image.open(path))

    def _capture_screen(self) -> None:
        self.showMinimized()
        QTimer.singleShot(500, self._do_capture)

    def _do_capture(self) -> None:
        try:
            screenshot = take_screenshot()
        except ScreenRecordingPermissionError as exc:
            self.showNormal()
            self.activateWindow()
            QMessageBox.warning(
                self,
                "Permission Required",
                str(exc),
            )
            return
        except Exception as exc:
            self.showNormal()
            self.activateWindow()
            QMessageBox.critical(
                self,
                "Capture Error",
                f"Could not capture screen:\n{exc}",
            )
            return

        self._screenshot_image = screenshot

        # Convert PIL Image to QPixmap for overlay
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        buf.seek(0)
        qpixmap = QPixmap()
        qpixmap.loadFromData(buf.read())

        self._overlay = SelectionOverlay(qpixmap)
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.cancelled.connect(self._on_capture_cancelled)
        self._overlay.show()

    def _on_region_selected(self, rect: QRect) -> None:
        cropped = crop_region(self._screenshot_image, rect)

        # Convert cropped PIL Image to QPixmap
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        buf.seek(0)
        qpixmap = QPixmap()
        qpixmap.loadFromData(buf.read())

        self.showNormal()
        self.activateWindow()
        self.preview.set_image(qpixmap)
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")

        self._executor.submit(self._run_ocr, cropped)

    def _on_capture_cancelled(self) -> None:
        self.showNormal()
        self.activateWindow()

    def _run_ocr(self, image: Image.Image) -> None:
        try:
            text = extract_text(image)
        except TesseractMissingError as exc:
            self._ocr_signals.error.emit(str(exc))
        except OCRError as exc:
            self._ocr_signals.error.emit(str(exc))
        except Exception as exc:
            self._ocr_signals.error.emit(f"Unexpected error: {exc}")
        else:
            self._ocr_signals.finished.emit(text)

    def _on_ocr_done(self, text: str) -> None:
        if text:
            self.preview.set_text(text)
            self.status_label.setText("Text extracted successfully.")
        else:
            self.preview.set_text("")
            self.status_label.setText("No text detected in this image.")
            QMessageBox.information(
                self,
                "No Text Detected",
                "OCR could not find any text in this image.",
            )

    def _on_ocr_error(self, message: str) -> None:
        self.status_label.setText("OCR failed.")
        QMessageBox.critical(
            self,
            "OCR Error",
            message,
        )


def main() -> None:
    """Launch the IMG2TXT application."""
    app = QApplication(sys.argv)
    app.setApplicationName("IMG2TXT")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
