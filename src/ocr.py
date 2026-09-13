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


def extract_text(
    image: Image.Image,
    *,
    preserve_layout: bool = False,
    indent_width: int = 2,
) -> str:
    """Run Tesseract OCR on a PIL Image.

    Args:
        image: A PIL Image to extract text from.
        preserve_layout: When True, reconstruct spacing
            and indentation from word bounding boxes
            instead of returning Tesseract's collapsed
            text. Useful for code or terminal output.
        indent_width: The number of spaces per indent
            level when ``preserve_layout`` is True.
            Leading spaces are snapped to the nearest
            multiple of this value.  Ignored when
            ``preserve_layout`` is False.

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
        if preserve_layout:
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
            )
            text = _reconstruct_layout(
                data,
                indent_width=indent_width,
            )
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


def _snap_to_multiple(value: int, unit: int) -> int:
    """Round *value* to the nearest multiple of *unit*.

    Args:
        value: The raw number of spaces.
        unit: The indent width to snap to.

    Returns:
        The nearest non-negative multiple of *unit*.
    """
    if unit <= 0:
        return max(value, 0)
    return max(round(value / unit) * unit, 0)


def _reconstruct_layout(
    data: dict,
    *,
    indent_width: int = 2,
) -> str:
    """Rebuild indentation and spacing from OCR word boxes.

    The algorithm normalises leading whitespace in three
    steps:

    1. **Baseline subtraction** — the smallest ``left``
       value among all first-words-on-each-line is
       subtracted so the leftmost text maps to column 0.
    2. **Snap to grid** — the resulting leading-space
       count is rounded to the nearest multiple of
       *indent_width* so indentation is always clean.
    3. **Max-increase clamp** — a line's indentation may
       increase by at most *indent_width* spaces relative
       to the previous line.  Decreases are unrestricted.

    Args:
        data: The dict returned by
            ``pytesseract.image_to_data`` with
            ``output_type=Output.DICT``.
        indent_width: Number of spaces per indent level.
            Leading spaces are snapped to the nearest
            multiple of this value.

    Returns:
        Text with leading indentation and inter-word
        gaps approximated from pixel positions.
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
    # character, used to convert pixel gaps to spaces.
    char_widths = [w["width"] / len(w["text"]) for w in words if w["text"]]
    char_width = sum(char_widths) / len(char_widths)
    if char_width <= 0:
        char_width = 1.0

    lines: dict[tuple[int, int, int], list[dict]] = {}
    for w in words:
        key = (w["block"], w["par"], w["line"])
        lines.setdefault(key, []).append(w)

    # Baseline: smallest left offset among all first
    # words so the leftmost line starts at column 0.
    min_left = min(lw[0]["left"] for lw in lines.values())

    rendered_lines = []
    prev_indent = 0
    for key in sorted(lines):
        line_words = lines[key]
        parts: list[str] = []
        prev_right = None
        for w in line_words:
            if prev_right is None:
                raw = round(
                    (w["left"] - min_left) / char_width,
                )
                leading = _snap_to_multiple(
                    raw,
                    indent_width,
                )
                # Clamp increases: indent may grow by at
                # most one indent_width per line.
                max_indent = prev_indent + indent_width
                if leading > max_indent:
                    leading = max_indent
                prev_indent = leading
                parts.append(" " * leading)
            else:
                gap = round(
                    (w["left"] - prev_right) / char_width,
                )
                parts.append(" " * max(gap, 1))
            parts.append(w["text"])
            prev_right = w["left"] + w["width"]
        rendered_lines.append("".join(parts))

    return "\n".join(rendered_lines)
