"""Screenshot capture utilities."""

from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path
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


def take_screenshot(
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Capture a screen region or the primary monitor.

    Args:
        region: Optional ``(x, y, width, height)`` in
            logical screen coordinates.  When *None* the
            primary monitor is captured.

    Returns a PIL Image of the captured area.

    Raises:
        ScreenRecordingPermissionError: If the OS
            denies screen recording access.
    """
    if platform.system() == "Darwin":
        try:
            return _take_screenshot_macos(region)
        except (subprocess.CalledProcessError, OSError):
            pass

        try:
            return _take_screenshot_mss(region)
        except mss.exception.ScreenShotError as exc:
            raise ScreenRecordingPermissionError(
                _MACOS_PERMISSION_MSG
            ) from exc

    return _take_screenshot_mss(region)


def _take_screenshot_macos(
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Capture via macOS native screencapture."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = ["screencapture", "-x"]
        if region is not None:
            x, y, w, h = region
            cmd.extend(["-R", f"{x},{y},{w},{h}"])
        cmd.append(tmp_path)
        subprocess.run(cmd, check=True)
        img = Image.open(tmp_path)
        img.load()  # force read before file cleanup
        return img
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _take_screenshot_mss(
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Capture via mss (cross-platform fallback)."""
    with mss.mss() as sct:
        if region is not None:
            x, y, w, h = region
            monitor = {
                "left": x,
                "top": y,
                "width": w,
                "height": h,
            }
        else:
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
