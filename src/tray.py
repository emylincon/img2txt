"""System tray icon with context menu for IMG2TXT."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

_ICON_PATH = Path(__file__).parent.parent / "assets" / "icon.png"


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu.

    Signals:
        capture_triggered: User clicked Capture Screen.
        open_image_triggered: User clicked Open Image.
        show_window_triggered: User clicked Show Window.
        quit_triggered: User clicked Quit.
    """

    capture_triggered = pyqtSignal()
    open_image_triggered = pyqtSignal()
    show_window_triggered = pyqtSignal()
    quit_triggered = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setIcon(QIcon(str(_ICON_PATH)))
        self.setToolTip("IMG2TXT — ready")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        """Build the tray context menu."""
        menu = QMenu()

        capture_action = QAction("Capture Screen", menu)
        capture_action.triggered.connect(self.capture_triggered)
        menu.addAction(capture_action)

        open_action = QAction("Open Image…", menu)
        open_action.triggered.connect(self.open_image_triggered)
        menu.addAction(open_action)

        menu.addSeparator()

        show_action = QAction("Show Window", menu)
        show_action.triggered.connect(self.show_window_triggered)
        menu.addAction(show_action)

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_triggered)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle main window on double-click / trigger."""
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.show_window_triggered.emit()
