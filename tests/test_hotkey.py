"""Tests for the global hotkey module."""

from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication

from src.hotkey import HotkeyManager, _hotkey_combo


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestHotkeyCombo:
    """Tests for platform-specific hotkey combo."""

    def test_macos_combo(self):
        """macOS uses Cmd+Shift+T."""
        with patch("src.hotkey.platform.system", return_value="Darwin"):
            assert _hotkey_combo() == "<cmd>+<shift>+t"

    def test_linux_combo(self):
        """Linux uses Ctrl+Shift+T."""
        with patch("src.hotkey.platform.system", return_value="Linux"):
            assert _hotkey_combo() == "<ctrl>+<shift>+t"

    def test_windows_combo(self):
        """Windows uses Ctrl+Shift+T."""
        with patch("src.hotkey.platform.system", return_value="Windows"):
            assert _hotkey_combo() == "<ctrl>+<shift>+t"


class TestHotkeyManager:
    """Tests for the HotkeyManager class."""

    def test_creates_without_error(self, qapp):
        """HotkeyManager can be instantiated."""
        mgr = HotkeyManager()
        assert mgr is not None

    def test_available_with_pynput(self, qapp):
        """available is True when pynput is installed."""
        mgr = HotkeyManager()
        assert mgr.available is True

    def test_available_without_pynput(self, qapp):
        """available is False when pynput is missing."""
        with patch("src.hotkey.GlobalHotKeys", None):
            mgr = HotkeyManager()
            assert mgr.available is False

    def test_start_returns_false_without_pynput(self, qapp):
        """start() returns False if pynput unavailable."""
        with patch("src.hotkey.GlobalHotKeys", None):
            mgr = HotkeyManager()
            assert mgr.start() is False

    def test_start_and_stop(self, qapp):
        """start() and stop() without error."""
        mgr = HotkeyManager()
        mgr.start()
        # May fail on CI without accessibility permissions
        # but should not raise
        mgr.stop()

    def test_stop_without_start(self, qapp):
        """stop() without start() does not raise."""
        mgr = HotkeyManager()
        mgr.stop()  # Should be a no-op
