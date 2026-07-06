"""Clipboard and sound feedback utilities."""

from __future__ import annotations

from pathlib import Path

import pyperclip
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect

ASSETS_DIR = Path(__file__).parent.parent / "assets"
SOUND_FILE = ASSETS_DIR / "success.wav"


def copy_and_notify(
    text: str,
    *,
    sound_effect: QSoundEffect | None = None,
) -> None:
    """Copy text to clipboard and play a sound.

    Args:
        text: The text to copy to the clipboard.
        sound_effect: Optional pre-loaded QSoundEffect.
            If None, a new one is created and played.
    """
    pyperclip.copy(text)

    if sound_effect is not None:
        sound_effect.play()
    elif SOUND_FILE.exists():
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(SOUND_FILE)))
        effect.setVolume(0.5)
        effect.play()
