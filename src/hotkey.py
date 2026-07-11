"""Global hotkey listener for IMG2TXT."""

from __future__ import annotations

import logging
import platform
import threading

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

try:
    from pynput.keyboard import GlobalHotKeys
except ImportError:
    GlobalHotKeys = None  # type: ignore[assignment,misc]


def _hotkey_combo() -> str:
    """Return the hotkey combo string for the current platform."""
    if platform.system() == "Darwin":
        return "<cmd>+<shift>+t"
    return "<ctrl>+<shift>+t"


class HotkeyManager(QObject):
    """Manages a global hotkey that emits a Qt signal.

    The listener runs on a daemon thread so it does not
    block the Qt event loop.

    Signals:
        hotkey_pressed: Emitted (thread-safe) when the
            global hotkey is pressed.
    """

    hotkey_pressed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._listener: GlobalHotKeys | None = None
        self._lock = threading.Lock()
        self._running = False

    @property
    def available(self) -> bool:
        """Return True if pynput is installed."""
        return GlobalHotKeys is not None

    def start(self) -> bool:
        """Start listening for the global hotkey.

        Returns True on success, False if pynput is
        unavailable or the listener could not start.
        """
        if not self.available:
            logger.warning("pynput is not installed; global hotkey disabled.")
            return False

        with self._lock:
            if self._running:
                return True

            combo = _hotkey_combo()
            try:
                self._listener = GlobalHotKeys({combo: self._on_hotkey})
                self._listener.daemon = True
                self._listener.start()
                self._running = True
                logger.info("Global hotkey %s registered.", combo)
            except Exception:
                logger.exception("Failed to start global hotkey listener.")
                self._listener = None
                return False

        return True

    def stop(self) -> None:
        """Stop the hotkey listener thread."""
        with self._lock:
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
            self._running = False

    def _on_hotkey(self) -> None:
        """Called from the pynput thread."""
        # Emit the signal; Qt will marshal it to the main
        # thread because hotkey_pressed is a pyqtSignal
        # and connections default to AutoConnection.
        self.hotkey_pressed.emit()
