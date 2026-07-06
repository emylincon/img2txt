"""Clipboard and sound feedback utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyperclip

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent.parent / "assets"
SOUND_FILE = ASSETS_DIR / "success.wav"


def _play_sound() -> None:
    """Play the success sound if available."""
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QSoundEffect
    except ImportError:
        log.debug("QtMultimedia unavailable; skipping sound")
        return

    if not SOUND_FILE.exists():
        return

    effect = QSoundEffect()
    effect.setSource(QUrl.fromLocalFile(str(SOUND_FILE)))
    effect.setVolume(0.5)
    effect.play()


def copy_and_notify(
    text: str,
    *,
    sound_effect: Any | None = None,
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
    else:
        _play_sound()
