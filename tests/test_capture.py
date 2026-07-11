"""Tests for the screenshot capture module."""

from unittest.mock import MagicMock, patch

import mss.exception
import pytest
from PIL import Image
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from src.capture import (
    ScreenRecordingPermissionError,
    _take_screenshot_macos,
    _take_screenshot_mss,
    crop_region,
    take_screenshot,
)


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestTakeScreenshot:
    """Tests for the take_screenshot function."""

    @patch("src.capture._take_screenshot_macos")
    @patch(
        "src.capture.platform.system",
        return_value="Darwin",
    )
    def test_uses_macos_on_darwin(self, mock_sys, mock_mac):
        """Verify macOS path is used on Darwin."""
        mock_mac.return_value = Image.new("RGB", (100, 50), "red")
        result = take_screenshot()
        mock_mac.assert_called_once()
        assert isinstance(result, Image.Image)

    @patch("src.capture._take_screenshot_mss")
    @patch(
        "src.capture.platform.system",
        return_value="Linux",
    )
    def test_uses_mss_on_linux(self, mock_sys, mock_mss_fn):
        """Verify mss fallback is used on non-Darwin."""
        mock_mss_fn.return_value = Image.new("RGB", (100, 50), "blue")
        result = take_screenshot()
        mock_mss_fn.assert_called_once()
        assert isinstance(result, Image.Image)

    @patch(
        "src.capture._take_screenshot_mss",
        side_effect=mss.exception.ScreenShotError(
            "could not create image from display"
        ),
    )
    @patch(
        "src.capture._take_screenshot_macos",
        side_effect=OSError("screencapture failed"),
    )
    @patch(
        "src.capture.platform.system",
        return_value="Darwin",
    )
    def test_raises_permission_error_on_macos(
        self, mock_sys, mock_mac, mock_mss_fn
    ):
        """Verify permission error on macOS."""
        with pytest.raises(
            ScreenRecordingPermissionError,
            match="Screen recording permission",
        ):
            take_screenshot()

    @patch("src.capture.mss.mss")
    def test_mss_returns_pil_image(self, mock_mss):
        """Verify _take_screenshot_mss returns PIL Image."""
        fake_shot = MagicMock()
        fake_shot.size = (100, 50)
        fake_shot.bgra = b"\x00\x00\xff\xff" * (100 * 50)

        mock_sct = MagicMock()
        mock_sct.monitors = [
            {},
            {
                "top": 0,
                "left": 0,
                "width": 100,
                "height": 50,
            },
        ]
        mock_sct.grab.return_value = fake_shot
        mock_mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss.return_value.__exit__ = MagicMock(return_value=False)

        result = _take_screenshot_mss()
        assert isinstance(result, Image.Image)
        assert result.width > 0
        assert result.height > 0
        assert result.mode == "RGB"

    @patch("src.capture.subprocess.run")
    @patch("src.capture.Image.open")
    def test_macos_screencapture(self, mock_open_img, mock_run):
        """Verify _take_screenshot_macos uses subprocess."""
        fake_img = Image.new("RGB", (200, 100), "green")
        fake_img.load()
        mock_open_img.return_value = fake_img

        result = _take_screenshot_macos()

        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0][0] == "screencapture"
        assert isinstance(result, Image.Image)


class TestCropRegion:
    """Tests for the crop_region function."""

    def test_crop_returns_correct_dimensions(self, qapp):
        """Verify crop returns image with correct size."""
        img = Image.new("RGB", (400, 300), color="white")
        rect = QRect(10, 20, 100, 50)

        result = crop_region(img, rect)

        assert result.width == 100
        assert result.height == 50

    def test_crop_returns_pil_image(self, qapp):
        """Verify crop returns a PIL Image."""
        img = Image.new("RGB", (400, 300), color="white")
        rect = QRect(0, 0, 200, 150)

        result = crop_region(img, rect)

        assert isinstance(result, Image.Image)

    def test_crop_preserves_content(self, qapp):
        """Verify crop preserves pixel content."""
        img = Image.new("RGB", (400, 300), color="red")
        rect = QRect(50, 50, 100, 100)

        result = crop_region(img, rect)

        # Spot-check pixels are red
        assert result.getpixel((0, 0)) == (255, 0, 0)
        assert result.getpixel((50, 50)) == (255, 0, 0)
        assert result.getpixel((99, 99)) == (255, 0, 0)

    def test_crop_full_image(self, qapp):
        """Verify cropping the full image works."""
        img = Image.new("RGB", (200, 100), color="blue")
        rect = QRect(0, 0, 200, 100)

        result = crop_region(img, rect)

        assert result.size == (200, 100)
