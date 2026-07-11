"""Tests for the system tray module."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.tray import TrayIcon


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestTrayIcon:
    """Tests for the TrayIcon class."""

    def test_creates_without_error(self, qapp):
        """TrayIcon can be instantiated."""
        tray = TrayIcon()
        assert tray is not None

    def test_tooltip(self, qapp):
        """Tray icon has the expected tooltip."""
        tray = TrayIcon()
        assert tray.toolTip() == "IMG2TXT — ready"

    def test_context_menu_actions(self, qapp):
        """Context menu contains the expected actions."""
        tray = TrayIcon()
        menu = tray.contextMenu()
        assert menu is not None
        actions = menu.actions()
        texts = [a.text() for a in actions if not a.isSeparator()]
        assert "Capture Screen" in texts
        assert "Open Image…" in texts
        assert "Show Window" in texts
        assert "Quit" in texts

    def test_signals_exist(self, qapp):
        """TrayIcon has the expected signals."""
        tray = TrayIcon()
        assert hasattr(tray, "capture_triggered")
        assert hasattr(tray, "open_image_triggered")
        assert hasattr(tray, "show_window_triggered")
        assert hasattr(tray, "quit_triggered")

    def test_capture_signal_emitted(self, qapp):
        """Capture Screen action emits capture_triggered."""
        tray = TrayIcon()
        received = []
        tray.capture_triggered.connect(lambda: received.append(True))
        menu = tray.contextMenu()
        for action in menu.actions():
            if action.text() == "Capture Screen":
                action.trigger()
                break
        assert received == [True]

    def test_open_image_signal_emitted(self, qapp):
        """Open Image action emits open_image_triggered."""
        tray = TrayIcon()
        received = []
        tray.open_image_triggered.connect(lambda: received.append(True))
        menu = tray.contextMenu()
        for action in menu.actions():
            if action.text() == "Open Image…":
                action.trigger()
                break
        assert received == [True]
