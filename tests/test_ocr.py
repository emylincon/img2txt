"""Tests for the OCR engine wrapper."""

from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from src.ocr import (
    TesseractMissingError,
    extract_text,
)


def _make_text_image(
    text: str = "Hello World",
) -> Image.Image:
    """Create a simple image with text for testing."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc",
            36,
        )
    except OSError:
        font = ImageFont.load_default()
    draw.text((10, 30), text, fill="black", font=font)
    return img


class TestExtractText:
    """Tests for the extract_text function."""

    @patch(
        "src.ocr.pytesseract.image_to_string",
        return_value="Hello World\n",
    )
    def test_with_text_image(self, mock_ocr):
        """Test OCR on an image containing text."""
        img = _make_text_image("Hello")
        result = extract_text(img)
        assert isinstance(result, str)
        assert result == "Hello World"
        mock_ocr.assert_called_once_with(img)

    @patch(
        "src.ocr.pytesseract.image_to_string",
        return_value="\n",
    )
    def test_with_blank_image(self, mock_ocr):
        """Test OCR on a blank image returns empty."""
        img = Image.new("RGB", (100, 100), "white")
        result = extract_text(img)
        assert result == ""

    def test_with_invalid_input(self):
        """Test that non-Image input raises TypeError."""
        with pytest.raises(TypeError):
            extract_text("not an image")

    def test_tesseract_not_found(self):
        """Test TesseractMissingError on missing bin."""
        from pytesseract import TesseractNotFoundError

        img = Image.new("RGB", (100, 100), "white")
        with (
            patch(
                "src.ocr.pytesseract.image_to_string",
                side_effect=TesseractNotFoundError(),
            ),
            pytest.raises(TesseractMissingError),
        ):
            extract_text(img)
