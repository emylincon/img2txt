"""Tests for the main application module."""

import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication

from src.main import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestMainWindow:
    """Tests for the MainWindow class."""

    def test_window_title(self, qapp):
        """Verify the window title is set correctly."""
        window = MainWindow()
        assert window.windowTitle() == "IMG2TXT"

    def test_minimum_size(self, qapp):
        """Verify the minimum window size."""
        window = MainWindow()
        assert window.minimumWidth() == 800
        assert window.minimumHeight() == 600

    def test_has_preview_widget(self, qapp):
        """Verify the preview widget is present."""
        window = MainWindow()
        assert window.preview is not None

    def test_has_menu_bar(self, qapp):
        """Verify the menu bar has File menu."""
        window = MainWindow()
        menus = window.menuBar().actions()
        assert len(menus) >= 1
        assert menus[0].text() == "&File"

    def test_status_bar_exists(self, qapp):
        """Verify status bar is created."""
        window = MainWindow()
        assert window.statusBar() is not None

    def test_close_event_hides_window(self, qapp):
        """Closing the window hides it instead of quitting."""
        window = MainWindow()
        window.show()
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted() is False
        assert window.isVisible() is False

    def test_code_mode_default_false(self, qapp):
        """Code Mode is off by default."""
        window = MainWindow()
        assert window._code_mode is False
        assert window.code_mode_action.isChecked() is False

    def test_code_mode_menu_action_exists(self, qapp):
        """File menu contains the Code Mode action."""
        window = MainWindow()
        file_menu = window.menuBar().actions()[0].menu()
        texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
        assert "&Code Mode" in texts

    def test_toggle_code_mode_updates_state(self, qapp):
        """Toggling the action updates _code_mode and emits signal."""
        window = MainWindow()
        received = []
        window.code_mode_changed.connect(received.append)
        window.code_mode_action.trigger()
        assert window._code_mode is True
        assert received == [True]

    def test_set_code_mode_syncs_without_signal(self, qapp):
        """_set_code_mode updates state without re-emitting."""
        window = MainWindow()
        received = []
        window.code_mode_changed.connect(received.append)
        window._set_code_mode(True)
        assert window._code_mode is True
        assert window.code_mode_action.isChecked() is True
        assert received == []
