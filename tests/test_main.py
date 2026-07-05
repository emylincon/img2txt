"""Tests for the main application module."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.main import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestMainWindow:
    """Tests for the MainWindow class."""

    def test_window_title(self, qapp):
        """Verify the window title is set correctly."""
        window = MainWindow()
        assert window.windowTitle() == "IMG2TXT"

    def test_minimum_size(self, qapp):
        """Verify the minimum window size is 800x600."""
        window = MainWindow()
        assert window.minimumWidth() == 800
        assert window.minimumHeight() == 600
