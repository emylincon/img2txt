"""Tests for the main application module."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication

from src.main import MainWindow
from src.selector import SelectionOverlay


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

    def test_second_capture_is_noop_while_overlay_active(self, qapp):
        """A second capture request is ignored while overlay exists."""
        window = MainWindow()
        overlay = MagicMock(spec=SelectionOverlay)
        overlay.isVisible.return_value = True
        window._overlay = overlay
        with patch.object(window, "showMinimized") as mock_min:
            window._capture_screen()
        mock_min.assert_not_called()
        assert window._capture_pending is False

    def test_second_capture_is_noop_while_pending(self, qapp):
        """A second capture request is ignored while a timer is pending."""
        window = MainWindow()
        window._capture_pending = True
        with patch.object(window, "showMinimized") as mock_min:
            window._capture_screen()
        mock_min.assert_not_called()

    def test_second_capture_is_noop_during_screenshot(self, qapp):
        """A second capture is ignored while take_screenshot is running."""
        window = MainWindow()
        window._capture_pending = True
        nested: list[bool] = []

        def _screenshot(_region):
            nested.append(window._capture_in_progress())
            window._capture_screen()
            return Image.new("RGB", (10, 10), color="white")

        with (
            patch("src.main.take_screenshot", side_effect=_screenshot),
            patch("src.main.SelectionOverlay") as mock_overlay_cls,
            patch.object(window, "showMinimized") as mock_min,
        ):
            overlay = MagicMock()
            mock_overlay_cls.return_value = overlay
            window._do_capture()

        assert nested == [True]
        mock_min.assert_not_called()
        overlay.show.assert_called_once()
        assert window._capture_pending is False
        assert window._overlay is overlay

    def test_capture_permission_error_finishes_capture(self, qapp):
        """Permission errors restore the window and clear pending."""
        from src.capture import ScreenRecordingPermissionError

        window = MainWindow()
        window._capture_pending = True
        with (
            patch(
                "src.main.take_screenshot",
                side_effect=ScreenRecordingPermissionError("denied"),
            ),
            patch("src.main.QMessageBox.warning") as mock_warn,
            patch.object(window, "_finish_capture") as mock_finish,
        ):
            window._do_capture()
        mock_finish.assert_called_once()
        mock_warn.assert_called_once()
        assert mock_warn.call_args[0][1] == "Permission Required"

    def test_close_event_quits_when_tray_unavailable(self, qapp):
        """Without a tray, close accepts so the app can quit."""
        window = MainWindow()
        window._hide_on_close = False
        window.show()
        event = QCloseEvent()
        window.closeEvent(event)
        assert event.isAccepted() is True

    def test_preview_region_ocrs_crop(self, qapp):
        """Selecting a preview region OCRs the cropped image."""
        window = MainWindow()
        image = Image.new("RGB", (100, 80), color="white")
        window._current_image = image
        with patch.object(window, "_start_ocr") as mock_ocr:
            window._on_preview_region(QRect(10, 10, 40, 30))
        mock_ocr.assert_called_once()
        cropped = mock_ocr.call_args[0][0]
        assert cropped.size == (40, 30)

    def test_preview_clear_ocrs_full_image(self, qapp):
        """Clearing the selection re-OCRs the full loaded image."""
        window = MainWindow()
        image = Image.new("RGB", (100, 80), color="white")
        window._current_image = image
        with patch.object(window, "_start_ocr") as mock_ocr:
            window._on_preview_cleared()
        mock_ocr.assert_called_once_with(image)

    def test_stale_ocr_result_is_ignored(self, qapp):
        """An older OCR generation must not overwrite a newer result."""
        window = MainWindow()
        window._ocr_generation = 2
        window._ocr_busy = True
        window._on_ocr_done(1, "stale")
        assert window.preview.text_edit.toPlainText() == ""
        assert window._ocr_busy is True

    def test_load_image_ocrs_full_file(self, qapp, tmp_path):
        """Opening an image OCRs the full file by default."""
        path = tmp_path / "sample.png"
        Image.new("RGB", (40, 30), color="white").save(path)
        window = MainWindow()
        with patch.object(window, "_start_ocr") as mock_ocr:
            window._load_image(str(path))
        mock_ocr.assert_called_once()
        loaded = mock_ocr.call_args[0][0]
        assert loaded.size == (40, 30)
        assert window._current_image is not None

    def test_load_image_invalid_file_shows_dialog(self, qapp, tmp_path):
        """A non-image file shows the Invalid Image dialog."""
        path = tmp_path / "not-an-image.txt"
        path.write_text("nope")
        window = MainWindow()
        with (
            patch("src.main.QMessageBox.warning") as mock_warn,
            patch.object(window, "_start_ocr") as mock_ocr,
        ):
            window._load_image(str(path))
        mock_ocr.assert_not_called()
        mock_warn.assert_called_once()
        assert mock_warn.call_args[0][1] == "Invalid Image"
