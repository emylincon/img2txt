"""File picker for selecting image files."""

from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QWidget

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"


def open_image_dialog(
    parent: QWidget | None = None,
) -> str | None:
    """Show a file dialog filtered to image types.

    Args:
        parent: Parent widget for the dialog.

    Returns:
        The selected file path, or None if the user
        cancelled the dialog.
    """
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Open Image",
        "",
        IMAGE_FILTER,
    )
    return path if path else None
