"""Screenshot capture utilities."""

from __future__ import annotations

import platform
import subprocess
import tempfile
from typing import TYPE_CHECKING

import mss
from PIL import Image

if TYPE_CHECKING:
    from PyQt6.QtCore import QRect


class ScreenRecordingPermissionError(Exception):
    """Raised when screen recording permission is denied."""


_MACOS_PERMISSION_MSG = (
    "Screen recording permission is required.\n\n"
    "To grant access:\n"
    "1. Open System Settings → Privacy & Security "
    "→ Screen Recording.\n"
    "2. Enable the toggle for your terminal app "
    "(e.g. Terminal, iTerm2, VS Code).\n"
    "3. Restart the app and try again."
)


def take_screenshot() -> Image.Image:
    """Capture the entire primary monitor.

    On macOS, tries the native ``screencapture`` command
    first, then falls back to ``mss``.  On other
    platforms ``mss`` is used directly.

    Returns a PIL Image of the full screen.

    Raises:
        ScreenRecordingPermissionError: If the OS
            denies screen recording access.
    """
    if platform.system() == "Darwin":
        try:
            return _take_screenshot_macos()
        except (subprocess.CalledProcessError, OSError):
            pass

        try:
            return _take_screenshot_mss()
        except mss.exception.ScreenShotError as exc:
            raise ScreenRecordingPermissionError(
                _MACOS_PERMISSION_MSG
            ) from exc

    return _take_screenshot_mss()


def _take_screenshot_macos() -> Image.Image:
    """Capture via macOS native screencapture."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run(
        ["screencapture", "-x", tmp_path],
        check=True,
    )
    img = Image.open(tmp_path)
    img.load()  # force read before file cleanup
    return img


def _take_screenshot_mss() -> Image.Image:
    """Capture via mss (cross-platform fallback)."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        shot = sct.grab(monitor)
        return Image.frombytes(
            "RGB",
            shot.size,
            shot.bgra,
            "raw",
            "BGRX",
        )


def crop_region(
    image: Image.Image,
    rect: QRect,
) -> Image.Image:
    """Crop a PIL Image to the given QRect.

    Args:
        image: The source PIL Image.
        rect: A QRect defining the crop region.

    Returns:
        A new PIL Image cropped to the rectangle.
    """
    box = (
        rect.x(),
        rect.y(),
        rect.x() + rect.width(),
        rect.y() + rect.height(),
    )
    return image.crop(box)
