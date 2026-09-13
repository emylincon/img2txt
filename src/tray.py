"""System tray icon with context menu for IMG2TXT."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

_ICON_PATH = Path(__file__).parent.parent / "assets" / "icon.png"

#: Indent-width choices exposed in the submenu.
INDENT_WIDTH_OPTIONS: tuple[int, ...] = (2, 4, 8)

#: Default indent width.
DEFAULT_INDENT_WIDTH: int = 2


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu.

    Signals:
        capture_triggered: User clicked Capture Screen.
        open_image_triggered: User clicked Open Image.
        show_window_triggered: User clicked Show Window.
        quit_triggered: User clicked Quit.
        layout_mode_toggled: User toggled Preserve Layout.
        indent_width_changed: User selected an indent width.
    """

    capture_triggered = pyqtSignal()
    open_image_triggered = pyqtSignal()
    show_window_triggered = pyqtSignal()
    quit_triggered = pyqtSignal()
    layout_mode_toggled = pyqtSignal(bool)
    indent_width_changed = pyqtSignal(int)

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

        self.layout_action = QAction("Preserve Layout", menu)
        self.layout_action.setCheckable(True)
        self.layout_action.toggled.connect(self.layout_mode_toggled)
        menu.addAction(self.layout_action)

        # --- Indent Width submenu ---
        self.indent_menu = QMenu("Indent Width", menu)
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
        menu.addMenu(self.indent_menu)

        # Enable/disable indent submenu with layout mode.
        self.layout_action.toggled.connect(
            self.indent_menu.setEnabled,
        )

        menu.addSeparator()

        show_action = QAction("Show Window", menu)
        show_action.triggered.connect(self.show_window_triggered)
        menu.addAction(show_action)

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_triggered)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_indent_action_triggered(
        self,
        action: QAction,
    ) -> None:
        """Emit indent_width_changed with the selected value."""
        self.indent_width_changed.emit(int(action.text()))

    def set_layout_mode(self, checked: bool) -> None:
        """Sync the Preserve Layout checkbox without re-emitting."""
        if self.layout_action.isChecked() != checked:
            self.layout_action.blockSignals(True)
            self.layout_action.setChecked(checked)
            self.layout_action.blockSignals(False)

    def set_indent_width(self, width: int) -> None:
        """Sync the Indent Width selection without re-emitting."""
        action = self._indent_actions.get(width)
        if action and not action.isChecked():
            self._indent_group.blockSignals(True)
            action.setChecked(True)
            self._indent_group.blockSignals(False)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle main window on double-click / trigger."""
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.show_window_triggered.emit()
