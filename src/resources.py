"""Resolve asset and bundled-binary paths for source and frozen apps."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return an absolute path, honoring PyInstaller.

    When frozen, files packed via ``datas`` / ``binaries`` live under
    ``sys._MEIPASS``.  Otherwise paths are resolved from the project
    root (the parent of ``src/``).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def configure_tesseract() -> None:
    """Point pytesseract at a bundled binary when running frozen.

    If no bundled Tesseract is present, leave the system PATH
    behaviour unchanged so the existing missing-binary error
    message still applies.
    """
    if not getattr(sys, "frozen", False):
        return

    import pytesseract

    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    candidates = (
        resource_path("tesseract", exe_name),
        resource_path(exe_name),
    )
    bundled = next((path for path in candidates if path.exists()), None)
    if bundled is None:
        return

    pytesseract.pytesseract.tesseract_cmd = str(bundled)

    tessdata_candidates = (
        resource_path("tesseract", "tessdata"),
        resource_path("tessdata"),
    )
    tessdata = next(
        (path for path in tessdata_candidates if path.is_dir()),
        None,
    )
    if tessdata is not None:
        os.environ["TESSDATA_PREFIX"] = str(tessdata)
