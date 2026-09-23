"""IMG2TXT application entry point."""

from __future__ import annotations

import io
import logging
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from PyQt6.QtCore import QObject, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QCursor,
    QKeyEvent,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
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
from src.tray import (
    DEFAULT_INDENT_WIDTH,
    INDENT_WIDTH_OPTIONS,
    TrayIcon,
)

logger = logging.getLogger(__name__)

# Delay (ms) before capturing to let the window minimise.
_CAPTURE_DELAY_MS = 500


def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL Image to a QPixmap."""
    if image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGBA")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    qpixmap = QPixmap()
    qpixmap.loadFromData(buf.getvalue())
    return qpixmap


class _OCRSignals(QObject):
    """Signals for OCR background task."""

    finished = pyqtSignal(int, str)
    error = pyqtSignal(int, str)


class MainWindow(QMainWindow):
    """Main application window."""

    layout_mode_changed = pyqtSignal(bool)
    indent_width_changed = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMG2TXT")
        self.setMinimumSize(800, 600)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._ocr_signals = _OCRSignals()
        self._ocr_signals.finished.connect(self._on_ocr_done)
        self._ocr_signals.error.connect(self._on_ocr_error)
        self._current_image: Image.Image | None = None
        self._screenshot_image: Image.Image | None = None
        self._overlay: SelectionOverlay | None = None
        self._capture_pending = False
        self._ocr_generation = 0
        self._ocr_busy = False
        self._pending_ocr: tuple[Image.Image, int, bool, int] | None = None
        self._hide_on_close = True
        self._preserve_layout = False
        self._indent_width = DEFAULT_INDENT_WIDTH
        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        self.preview = PreviewWidget()
        self.preview.region_selected.connect(self._on_preview_region)
        self.preview.selection_cleared.connect(self._on_preview_cleared)
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

        self.layout_action = QAction("Preserve &Layout", self)
        self.layout_action.setCheckable(True)
        self.layout_action.toggled.connect(self._toggle_layout_mode)
        file_menu.addAction(self.layout_action)

        # --- Indent Width submenu ---
        self.indent_menu = file_menu.addMenu("&Indent Width")
        self.indent_menu.setEnabled(False)
        self._indent_group = QActionGroup(self.indent_menu)
        self._indent_group.setExclusive(True)
        self._indent_actions: dict[int, QAction] = {}

        for width in INDENT_WIDTH_OPTIONS:
            action = QAction(str(width), self.indent_menu)
            action.setCheckable(True)
            if width == DEFAULT_INDENT_WIDTH:
                action.setChecked(True)
            self._indent_group.addAction(action)
            self.indent_menu.addAction(action)
            self._indent_actions[width] = action

        self._indent_group.triggered.connect(
            self._on_indent_action_triggered,
        )

        # Enable/disable indent submenu with layout mode.
        self.layout_action.toggled.connect(
            self.indent_menu.setEnabled,
        )

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
        """Hide to tray when a tray icon exists; otherwise quit."""
        if self._hide_on_close:
            event.ignore()
            self.hide()
            return
        event.accept()

    def keyPressEvent(  # noqa: N802
        self, event: QKeyEvent
    ) -> None:
        """Forward Escape to the preview selector."""
        if event.key() == Qt.Key.Key_Escape:
            self.preview.image_label.clear_selection()
            return
        super().keyPressEvent(event)

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

        try:
            with Image.open(path) as src:
                transposed = ImageOps.exif_transpose(src)
                image = transposed.copy()
        except (OSError, UnidentifiedImageError):
            QMessageBox.warning(
                self,
                "Invalid Image",
                f"Could not load image:\n{path}",
            )
            return

        try:
            pixmap = _pil_to_qpixmap(image)
        except OSError:
            QMessageBox.warning(
                self,
                "Invalid Image",
                f"Could not load image:\n{path}",
            )
            return
        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Invalid Image",
                f"Could not load image:\n{path}",
            )
            return

        self._current_image = image
        self.preview.set_image(pixmap)
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")
        self._start_ocr(image)

    def _capture_in_progress(self) -> bool:
        return self._capture_pending or self._overlay is not None

    def _capture_screen(self) -> None:
        if self._capture_in_progress():
            return
        self._capture_pending = True
        self.showMinimized()
        QTimer.singleShot(_CAPTURE_DELAY_MS, self._do_capture)

    def _do_capture(self) -> None:
        if self._overlay is not None and self._overlay.isVisible():
            self._capture_pending = False
            return

        # Determine which screen the cursor is on so we
        # capture and overlay the correct monitor.
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            self._finish_capture()
            QMessageBox.critical(
                self,
                "Capture Error",
                "No screen is available.",
            )
            return
        self._capture_target_screen = screen

        geom = screen.geometry()
        region = (
            geom.x(),
            geom.y(),
            geom.width(),
            geom.height(),
        )

        try:
            screenshot = take_screenshot(region)
            qpixmap = _pil_to_qpixmap(screenshot)
            self._screenshot_image = screenshot
            self._overlay = SelectionOverlay(qpixmap, screen)
            self._overlay.region_selected.connect(self._on_region_selected)
            self._overlay.cancelled.connect(self._on_capture_cancelled)
            self._overlay.show()
        except ScreenRecordingPermissionError as exc:
            self._finish_capture()
            QMessageBox.warning(
                self,
                "Permission Required",
                str(exc),
            )
            return
        except Exception as exc:
            self._finish_capture()
            QMessageBox.critical(
                self,
                "Capture Error",
                f"Could not capture screen:\n{exc}",
            )
            return
        self._capture_pending = False

    def _finish_capture(self) -> None:
        self._capture_pending = False
        if self._overlay is not None:
            self._overlay.close()
            self._overlay.deleteLater()
            self._overlay = None
        self._screenshot_image = None
        self.showNormal()
        self.activateWindow()

    def _on_region_selected(self, rect: QRect) -> None:
        # Scale selection from logical points to physical
        # pixels for HiDPI / Retina displays.
        screen = getattr(self, "_capture_target_screen", None)
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

        self._current_image = cropped
        self._finish_capture()
        self.preview.set_image(qpixmap)
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")
        self._start_ocr(cropped)

    def _on_capture_cancelled(self) -> None:
        self._finish_capture()

    def _on_preview_region(self, rect: QRect) -> None:
        if self._current_image is None:
            return
        cropped = crop_region(self._current_image, rect)
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")
        self._start_ocr(cropped)

    def _on_preview_cleared(self) -> None:
        if self._current_image is None:
            return
        self.preview.set_text("")
        self.preview.copy_btn.setEnabled(False)
        self.status_label.setText("Extracting text…")
        self._start_ocr(self._current_image)

    def _toggle_layout_mode(self, checked: bool) -> None:
        self._preserve_layout = checked
        self.layout_mode_changed.emit(checked)

    def _on_indent_action_triggered(
        self,
        action: QAction,
    ) -> None:
        """Handle indent-width radio selection."""
        self._indent_width = int(action.text())
        self.indent_width_changed.emit(self._indent_width)

    def _set_layout_mode(self, checked: bool) -> None:
        """Sync layout mode from an external source (e.g. tray)."""
        self._preserve_layout = checked
        if self.layout_action.isChecked() != checked:
            self.layout_action.blockSignals(True)
            self.layout_action.setChecked(checked)
            self.layout_action.blockSignals(False)

    def _set_indent_width(self, width: int) -> None:
        """Sync indent width from an external source (e.g. tray)."""
        self._indent_width = width
        action = self._indent_actions.get(width)
        if action and not action.isChecked():
            self._indent_group.blockSignals(True)
            action.setChecked(True)
            self._indent_group.blockSignals(False)

    def _start_ocr(self, image: Image.Image) -> None:
        """Queue OCR, replacing any in-flight result."""
        self._ocr_generation += 1
        self._pending_ocr = (
            image.copy(),
            self._ocr_generation,
            self._preserve_layout,
            self._indent_width,
        )
        if self._ocr_busy:
            return
        self._dispatch_ocr()

    def _dispatch_ocr(self) -> None:
        if self._pending_ocr is None:
            self._ocr_busy = False
            return
        image, generation, preserve_layout, indent_width = self._pending_ocr
        self._pending_ocr = None
        self._ocr_busy = True
        self._executor.submit(
            self._run_ocr,
            image,
            generation,
            preserve_layout,
            indent_width,
        )

    def _finish_ocr_job(self) -> None:
        self._ocr_busy = False
        self._dispatch_ocr()

    def _run_ocr(
        self,
        image: Image.Image,
        generation: int,
        preserve_layout: bool,
        indent_width: int,
    ) -> None:
        try:
            text = extract_text(
                image,
                preserve_layout=preserve_layout,
                indent_width=indent_width,
            )
        except TesseractMissingError as exc:
            self._ocr_signals.error.emit(generation, str(exc))
        except OCRError as exc:
            self._ocr_signals.error.emit(generation, str(exc))
        except Exception as exc:
            self._ocr_signals.error.emit(
                generation,
                f"Unexpected error: {exc}",
            )
        else:
            self._ocr_signals.finished.emit(generation, text)

    def _on_ocr_done(self, generation: int, text: str) -> None:
        try:
            if generation != self._ocr_generation:
                return
            self.preview.set_monospace(self._preserve_layout)
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
        finally:
            self._finish_ocr_job()

    def _on_ocr_error(self, generation: int, message: str) -> None:
        try:
            if generation != self._ocr_generation:
                return
            self.status_label.setText("OCR failed.")
            QMessageBox.critical(
                self,
                "OCR Error",
                message,
            )
        finally:
            self._finish_ocr_job()


def main() -> None:
    """Launch the IMG2TXT application."""
    app = QApplication(sys.argv)
    app.setApplicationName("IMG2TXT")

    window = MainWindow()
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    window._hide_on_close = tray_available
    app.setQuitOnLastWindowClosed(not tray_available)

    # --- System tray ---
    if tray_available:
        tray = TrayIcon()
        tray.capture_triggered.connect(window._capture_screen)
        tray.open_image_triggered.connect(window._open_image)
        tray.show_window_triggered.connect(window.showNormal)
        tray.show_window_triggered.connect(window.activateWindow)
        tray.quit_triggered.connect(app.quit)
        tray.layout_mode_toggled.connect(window._set_layout_mode)
        window.layout_mode_changed.connect(tray.set_layout_mode)
        tray.indent_width_changed.connect(window._set_indent_width)
        window.indent_width_changed.connect(tray.set_indent_width)
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
    app.aboutToQuit.connect(lambda: window._executor.shutdown(wait=False))

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
