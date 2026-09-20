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


def _collect_tesseract() -> tuple[list, list]:
    """Best-effort Tesseract binary + English tessdata.

    Windows installers are self-contained (exe + sibling
    DLLs). Unix binaries are dynlinked against Homebrew/apt
    libs that PyInstaller will not collect, so those
    platforms skip bundling and use a system Tesseract.
    """
    binaries: list[tuple[str, str]] = []
    datas: list[tuple[str, str]] = []
    if sys.platform != "win32":
        return binaries, datas

    exe = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if exe is None:
        return binaries, datas

    exe_path = Path(exe).resolve()
    dest = "tesseract"
    binaries.append((str(exe_path), dest))
    for dll in exe_path.parent.glob("*.dll"):
        binaries.append((str(dll), dest))

    candidates = [
        exe_path.parent / "tessdata",
        exe_path.parent.parent / "share" / "tessdata",
        exe_path.parent.parent / "share" / "tesseract-ocr" / "tessdata",
        Path("/usr/share/tesseract-ocr/5/tessdata"),
        Path("/usr/share/tesseract-ocr/4.00/tessdata"),
        Path("/usr/share/tessdata"),
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/local/share/tessdata"),
    ]
    prefix = os.environ.get("TESSDATA_PREFIX")
    if prefix:
        candidates.insert(0, Path(prefix))

    for candidate in candidates:
        if (candidate / "eng.traineddata").is_file():
            datas.append((str(candidate), "tesseract/tessdata"))
            break
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
