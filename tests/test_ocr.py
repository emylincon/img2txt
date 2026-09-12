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


class TestExtractTextPreserveLayout:
    """Tests for the code_mode OCR path."""

    _SAMPLE_DATA = {
        "block_num": [1, 1, 1],
        "par_num": [1, 1, 1],
        "line_num": [1, 1, 2],
        "left": [0, 100, 20],
        "width": [30, 30, 30],
        "text": ["def", "foo():", "pass"],
        "conf": [95, 95, 95],
    }

    @patch("src.ocr.pytesseract.image_to_data")
    def test_calls_image_to_data(self, mock_data):
        """code_mode=True should call image_to_data."""
        mock_data.return_value = self._SAMPLE_DATA
        img = Image.new("RGB", (200, 100), "white")
        result = extract_text(img, code_mode=True)
        mock_data.assert_called_once()
        assert "def" in result
        assert "pass" in result

    @patch("src.ocr.pytesseract.image_to_data")
    def test_indentation_from_left_offset(self, mock_data):
        """Leading tabs reflect the word's left pixel offset."""
        mock_data.return_value = self._SAMPLE_DATA
        img = Image.new("RGB", (200, 100), "white")
        result = extract_text(img, code_mode=True)
        lines = result.split("\n")
        # Second line's word starts at left=20, first line at left=0.
        assert lines[1].startswith("\t")
        assert not lines[0].startswith("\t")

    @patch("src.ocr.pytesseract.image_to_data")
    def test_inter_word_gap(self, mock_data):
        """Spaces (not tabs) appear between far-apart words."""
        mock_data.return_value = self._SAMPLE_DATA
        img = Image.new("RGB", (200, 100), "white")
        result = extract_text(img, code_mode=True)
        first_line = result.split("\n")[0]
        assert "def" in first_line
        assert "foo():" in first_line
        gap = first_line[len("def") : first_line.index("foo():")]
        assert gap == " " * len(gap)
        assert len(gap) >= 1

    @patch("src.ocr.pytesseract.image_to_data")
    def test_multiline_output(self, mock_data):
        """Lines are separated by newlines."""
        mock_data.return_value = self._SAMPLE_DATA
        img = Image.new("RGB", (200, 100), "white")
        result = extract_text(img, code_mode=True)
        assert len(result.split("\n")) == 2

    @patch("src.ocr.pytesseract.image_to_data")
    def test_empty_data_returns_empty_string(self, mock_data):
        """No confident words should yield an empty string."""
        mock_data.return_value = {
            "block_num": [],
            "par_num": [],
            "line_num": [],
            "left": [],
            "width": [],
            "text": [],
            "conf": [],
        }
        img = Image.new("RGB", (100, 100), "white")
        result = extract_text(img, code_mode=True)
        assert result == ""

    @patch(
        "src.ocr.pytesseract.image_to_string",
        return_value="Hello World\n",
    )
    def test_plain_mode_unchanged(self, mock_ocr):
        """code_mode=False keeps calling image_to_string."""
        img = _make_text_image("Hello")
        result = extract_text(img, code_mode=False)
        assert result == "Hello World"
        mock_ocr.assert_called_once_with(img)
