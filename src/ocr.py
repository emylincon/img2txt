"""OCR engine wrapper using Tesseract."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytesseract
from pytesseract import TesseractNotFoundError

if TYPE_CHECKING:
    from PIL import Image


class OCRError(Exception):
    """Raised when OCR processing fails."""


class TesseractMissingError(OCRError):
    """Raised when Tesseract is not installed."""


def extract_text(image: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image.

    Args:
        image: A PIL Image to extract text from.

    Returns:
        The extracted text string, stripped of
        leading/trailing whitespace.

    Raises:
        TesseractMissingError: If Tesseract is not
            installed on the system.
        OCRError: If OCR processing fails for any
            other reason.
        TypeError: If the input is not a PIL Image.
    """
    if not hasattr(image, "mode"):
        msg = "Expected a PIL Image instance."
        raise TypeError(msg)

    try:
        text: str = pytesseract.image_to_string(image)
    except TesseractNotFoundError as exc:
        msg = (
            "Tesseract is not installed or not found "
            "in PATH. Please install Tesseract OCR:\n"
            "  macOS:   brew install tesseract\n"
            "  Ubuntu:  sudo apt install tesseract-ocr\n"
            "  Windows: download from "
            "github.com/UB-Mannheim/tesseract/wiki"
        )
        raise TesseractMissingError(msg) from exc
    except Exception as exc:
        msg = f"OCR processing failed: {exc}"
        raise OCRError(msg) from exc

    return text.strip()
