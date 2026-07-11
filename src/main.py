"""IMG2TXT application entry point."""

from __future__ import annotations

import io
import logging
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QObject, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QCursor, QPixmap
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
from src.hotkey import HotkeyManager
from src.ocr import (
    OCRError,
    TesseractMissingError,
    extract_text,
)
from src.picker import open_image_dialog
from src.preview import PreviewWidget
from src.selector import SelectionOverlay
from src.tray import TrayIcon

logger = logging.getLogger(__name__)

# Delay (ms) before capturing to let the window minimise.
_CAPTURE_DELAY_MS = 500


def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL Image to a QPixmap."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    qpixmap = QPixmap()
    qpixmap.loadFromData(buf.getvalue())
    return qpixmap


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
        self._screenshot_image: Image.Image | None = None
        self._overlay: SelectionOverlay | None = None
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
        capture_action.triggered.connect(self._capture_screen)
        file_menu.addAction(capture_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(
            QApplication.instance().quit  # type: ignore[union-attr]
        )
        file_menu.addAction(quit_action)

    def closeEvent(  # noqa: N802
        self, event: QCloseEvent
    ) -> None:
        """Hide window instead of quitting."""
        event.ignore()
        self.hide()

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
        QTimer.singleShot(_CAPTURE_DELAY_MS, self._do_capture)

    def _do_capture(self) -> None:
        # Determine which screen the cursor is on so we
        # capture and overlay the correct monitor.
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        self._capture_screen = screen

        geom = screen.geometry()
        region = (
            geom.x(),
            geom.y(),
            geom.width(),
            geom.height(),
        )

        try:
            screenshot = take_screenshot(region)
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
        qpixmap = _pil_to_qpixmap(screenshot)

        self._overlay = SelectionOverlay(qpixmap, screen)
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.cancelled.connect(self._on_capture_cancelled)
        self._overlay.show()

    def _on_region_selected(self, rect: QRect) -> None:
        # Scale selection from logical points to physical
        # pixels for HiDPI / Retina displays.
        screen = getattr(self, "_capture_screen", None)
        if screen is None:
            screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0
        scaled_rect = QRect(
            int(rect.x() * ratio),
            int(rect.y() * ratio),
            int(rect.width() * ratio),
            int(rect.height() * ratio),
        )
        cropped = crop_region(self._screenshot_image, scaled_rect)

        # Convert cropped PIL Image to QPixmap
        qpixmap = _pil_to_qpixmap(cropped)

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
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()

    # --- System tray ---
    tray = TrayIcon()
    tray.capture_triggered.connect(window._capture_screen)
    tray.open_image_triggered.connect(window._open_image)
    tray.show_window_triggered.connect(window.showNormal)
    tray.show_window_triggered.connect(window.activateWindow)
    tray.quit_triggered.connect(app.quit)
    tray.show()

    # --- Global hotkey ---
    hotkey = HotkeyManager()
    hotkey.hotkey_pressed.connect(window._capture_screen)

    if not hotkey.start() and platform.system() == "Darwin":
        QMessageBox.warning(
            window,
            "Accessibility Permission Required",
            "IMG2TXT needs Accessibility permissions to "
            "register a global hotkey.\n\n"
            "Go to System Settings → Privacy & Security "
            "→ Accessibility and grant access to this "
            "application.\n\n"
            "The tray menu will still work without the "
            "hotkey.",
        )

    app.aboutToQuit.connect(hotkey.stop)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
