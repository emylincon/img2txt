# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for IMG2TXT.

Assets live under ``assets/`` and are resolved via
``src.resources.resource_path``.  Windows builds copy a
relocatable Tesseract tree (exe + sibling DLLs + tessdata)
when a system install is present.  Unix binaries are
dynlinked against Homebrew/apt libs that PyInstaller will
not collect, so those platforms skip the binary and the
frozen app uses a system Tesseract at runtime.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    *collect_submodules("pynput"),
    *collect_submodules("mss"),
    "pytesseract",
    "PIL",
    "PyQt6.QtMultimedia",
    "src.capture",
    "src.clipboard",
    "src.hotkey",
    "src.ocr",
    "src.picker",
    "src.preview",
    "src.resources",
    "src.selector",
    "src.tray",
]


def _windows_tesseract_exe() -> Path | None:
    """Return a real Tesseract exe, ignoring Chocolatey shims."""
    program_files = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(
            os.environ.get(
                "PROGRAMFILES(X86)",
                r"C:\Program Files (x86)",
            )
        ),
    ]
    for root in program_files:
        candidate = root / "Tesseract-OCR" / "tesseract.exe"
        if candidate.is_file():
            return candidate

    which = shutil.which("tesseract") or shutil.which(
        "tesseract.exe"
    )
    if which is None:
        return None
    path = Path(which).resolve()
    # Reject Chocolatey shims: they have no sibling tessdata.
    if not (path.parent / "tessdata" / "eng.traineddata").is_file():
        return None
    return path


def _collect_tesseract() -> tuple[list, list]:
    """Collect a relocatable Tesseract tree on Windows.

    Windows installers are self-contained (exe + sibling
    DLLs). Unix binaries are dynlinked against Homebrew/apt
    libs that PyInstaller will not collect, so those
    platforms skip bundling and use a system Tesseract.
    """
    binaries: list[tuple[str, str]] = []
    datas: list[tuple[str, str]] = []
    if sys.platform != "win32":
        return binaries, datas

    exe_path = _windows_tesseract_exe()
    if exe_path is None:
        raise SystemExit(
            "Windows builds require a real Tesseract install "
            "(tesseract.exe + tessdata), not only a PATH shim."
        )

    dest = "tesseract"
    binaries.append((str(exe_path), dest))
    for dll in exe_path.parent.glob("*.dll"):
        binaries.append((str(dll), dest))

    tessdata = exe_path.parent / "tessdata"
    if not (tessdata / "eng.traineddata").is_file():
        raise SystemExit(
            "eng.traineddata not found next to tesseract.exe"
        )
    datas.append((str(tessdata), "tesseract/tessdata"))
    return binaries, datas


tesseract_binaries, tesseract_datas = _collect_tesseract()

a = Analysis(
    ["src/main.py"],
    pathex=[],
    binaries=tesseract_binaries,
    datas=[("assets", "assets"), *tesseract_datas],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="img2txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=sys.platform == "darwin",
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="img2txt",
)
