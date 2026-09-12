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


# Number of characters a pixel gap must span before it is
# rendered as a single tab in Code Mode output. E.g. with
# the default of 2, a gap of 5 characters becomes 3 tabs
# (round(5 / 2)).
CHARS_PER_TAB = 2


def extract_text(
    image: Image.Image,
    *,
    code_mode: bool = False,
) -> str:
    """Run Tesseract OCR on a PIL Image.

    Args:
        image: A PIL Image to extract text from.
        code_mode: When True, reconstruct spacing and
            indentation from word bounding boxes using
            tab characters instead of returning
            Tesseract's collapsed text. Useful for code
            or terminal output.

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
        if code_mode:
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
            )
            text = _reconstruct_code_layout(data)
        else:
            text = pytesseract.image_to_string(image)
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


def _reconstruct_code_layout(data: dict) -> str:
    """Rebuild indentation and spacing from OCR word boxes.

    Only the leading indentation at the start of each line
    is rendered as tab characters, sized by
    ``CHARS_PER_TAB``. Inter-word gaps within a line are
    rendered as spaces.

    Args:
        data: The dict returned by
            ``pytesseract.image_to_data`` with
            ``output_type=Output.DICT``.

    Returns:
        Text with leading indentation rendered as tabs
        and inter-word gaps rendered as spaces,
        approximated from pixel positions.
    """
    n = len(data.get("text", []))
    words = []
    for i in range(n):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        words.append(
            {
                "block": data["block_num"][i],
                "par": data["par_num"][i],
                "line": data["line_num"][i],
                "left": data["left"][i],
                "width": data["width"][i],
                "text": text,
            }
        )

    if not words:
        return ""

    # Estimate the average pixel width of a single
    # character, used to convert pixel gaps to tabs.
    char_widths = [w["width"] / len(w["text"]) for w in words if w["text"]]
    char_width = sum(char_widths) / len(char_widths)
    if char_width <= 0:
        char_width = 1.0

    tab_width = char_width * CHARS_PER_TAB

    lines: dict[tuple[int, int, int], list[dict]] = {}
    for w in words:
        key = (w["block"], w["par"], w["line"])
        lines.setdefault(key, []).append(w)

    rendered_lines = []
    for key in sorted(lines):
        line_words = lines[key]
        parts: list[str] = []
        prev_right = None
        for w in line_words:
            if prev_right is None:
                leading = round(w["left"] / tab_width)
                parts.append("\t" * max(leading, 0))
            else:
                gap = round((w["left"] - prev_right) / char_width)
                parts.append(" " * max(gap, 1))
            parts.append(w["text"])
            prev_right = w["left"] + w["width"]
        rendered_lines.append("".join(parts))

    return "\n".join(rendered_lines)
