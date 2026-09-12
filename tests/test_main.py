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

    def test_layout_mode_default_false(self, qapp):
        """Preserve Layout is off by default."""
        window = MainWindow()
        assert window._preserve_layout is False
        assert window.layout_action.isChecked() is False

    def test_preserve_layout_menu_action_exists(self, qapp):
        """File menu contains the Preserve Layout action."""
        window = MainWindow()
        file_menu = window.menuBar().actions()[0].menu()
        texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
        assert "Preserve &Layout" in texts

    def test_toggle_layout_mode_updates_state(self, qapp):
        """Toggling the action updates _preserve_layout and emits signal."""
        window = MainWindow()
        received = []
        window.layout_mode_changed.connect(received.append)
        window.layout_action.trigger()
        assert window._preserve_layout is True
        assert received == [True]

    def test_set_layout_mode_syncs_without_signal(self, qapp):
        """_set_layout_mode updates state without re-emitting."""
        window = MainWindow()
        received = []
        window.layout_mode_changed.connect(received.append)
        window._set_layout_mode(True)
        assert window._preserve_layout is True
        assert window.layout_action.isChecked() is True
        assert received == []

    def test_indent_width_default(self, qapp):
        """Default indent width is 2."""
        window = MainWindow()
        assert window._indent_width == 2

    def test_indent_width_menu_exists(self, qapp):
        """File menu contains the Indent Width submenu."""
        window = MainWindow()
        file_menu = window.menuBar().actions()[0].menu()
        texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
        assert "&Indent Width" in texts

    def test_indent_width_menu_disabled_by_default(self, qapp):
        """Indent Width submenu is disabled when layout mode is off."""
        window = MainWindow()
        assert window.indent_menu.isEnabled() is False

    def test_indent_width_menu_enabled_with_layout(self, qapp):
        """Indent Width submenu is enabled when layout mode is on."""
        window = MainWindow()
        window.layout_action.setChecked(True)
        assert window.indent_menu.isEnabled() is True

    def test_indent_width_radio_updates_state(self, qapp):
        """Selecting an indent width updates _indent_width."""
        window = MainWindow()
        received = []
        window.indent_width_changed.connect(received.append)
        window._indent_actions[4].trigger()
        assert window._indent_width == 4
        assert received == [4]

    def test_set_indent_width_syncs_without_signal(self, qapp):
        """_set_indent_width updates state without re-emitting."""
        window = MainWindow()
        received = []
        window.indent_width_changed.connect(received.append)
        window._set_indent_width(4)
        assert window._indent_width == 4
        assert window._indent_actions[4].isChecked() is True
        assert received == []
