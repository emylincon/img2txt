"""Tests for the main application module."""

import pytest
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
