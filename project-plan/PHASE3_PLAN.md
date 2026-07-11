# Phase 3 — System Tray and Global Hotkey

## Goal

Move the application into the system tray so it runs
persistently in the background, add a tray context menu
for quick access to all actions, and register a global
hotkey (`Cmd+Shift+T` on macOS, `Ctrl+Shift+T`
elsewhere) that triggers screen capture from any context
without the main window being visible.

## Prerequisites

- Phase 2 complete and all tests passing.
- `pynput` library installed (`pynput>=1.7`).
- On macOS the user must grant Accessibility permissions
  to the terminal or app for `pynput` to work.

## Step-by-Step Implementation

### Step 1 — Add `pynput` Dependency

Install `pynput` and update `requirements.txt`.

**Tasks:**

1. Run `pip install "pynput>=1.7"`.
2. Add `pynput>=1.7` to `requirements.txt`.
3. Verify import:
   `python -c "from pynput import keyboard; print('ok')"`.

**Done when:** `pynput` imports without error.

### Step 2 — System Tray Module (`src/tray.py`)

Create a system tray icon with a context menu.

**Tasks:**

1. Create `src/tray.py` with a `TrayIcon` class that
   extends `QSystemTrayIcon`.
2. Add a tray icon image at `assets/icon.png` (a simple
   "T" glyph or text-extraction icon, 64 × 64 px).
3. Build a context menu with three actions:
   - **Capture Screen** — triggers the screenshot flow.
   - **Open Image…** — triggers the file picker flow.
   - **Quit** — exits the application.
4. Emit custom signals so `main.py` can connect each
   action to the existing handlers:

```python
class TrayIcon(QSystemTrayIcon):
    capture_triggered = pyqtSignal()
    open_image_triggered = pyqtSignal()
    quit_triggered = pyqtSignal()
```

5. Show a tooltip on the tray icon: "IMG2TXT — ready".
6. On tray icon double-click (or single-click on macOS),
   show/hide the main window via an `activated` signal
   handler.

**Done when:** The tray icon appears in the system tray
with a working context menu that prints debug messages
for each action.

### Step 3 — Global Hotkey Module (`src/hotkey.py`)

Register a system-wide keyboard shortcut.

**Tasks:**

1. Create `src/hotkey.py` with a `HotkeyManager` class:

```python
class HotkeyManager:
    def __init__(self) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

2. Use `pynput.keyboard.GlobalHotKeys` to listen for
   `<cmd>+<shift>+t` (macOS) or `<ctrl>+<shift>+t`.
3. Detect the platform at init time to pick the correct
   modifier key.
4. Run the listener on a daemon thread so it does not
   block the Qt event loop.
5. Emit a Qt signal (`hotkey_pressed`) back to the main
   thread using `QMetaObject.invokeMethod` or a
   `pyqtSignal` bridge to ensure thread safety.
6. Handle the case where Accessibility permissions are
   not granted on macOS — catch the error and surface a
   user-friendly message.
7. Write `tests/test_hotkey.py`:
   - Test that `HotkeyManager` starts and stops without
     error.
   - Test platform detection picks the correct modifier.

**Done when:** `pytest tests/test_hotkey.py` passes and
a manual test confirms the hotkey triggers a callback.

### Step 4 — Background Lifecycle Management

Keep the app alive when the main window is closed.

**Tasks:**

1. Set `QApplication.setQuitOnLastWindowClosed(False)`
   so the app stays alive when the window is hidden.
2. Override `MainWindow.closeEvent` to hide the window
   instead of quitting — the tray icon keeps running.
3. Add a "Show Window" action to the tray context menu
   (above Quit) that calls `MainWindow.showNormal()`
   and `MainWindow.activateWindow()`.
4. Wire the **Quit** tray action to
   `QApplication.quit()` to fully terminate the process.
5. On application startup, start the `HotkeyManager`.
6. On application shutdown (`aboutToQuit` signal), stop
   the `HotkeyManager` listener thread cleanly.

**Done when:** Closing the window hides it; the tray
icon remains; Quit from the tray exits the process.

### Step 5 — Wire Everything in `main.py`

Connect the tray, hotkey, and existing flows.

**Tasks:**

1. In `main()`, create the `TrayIcon` and call
   `tray.show()` before `window.show()`.
2. Connect tray signals to `MainWindow` slots:
   - `capture_triggered` → `_capture_screen`.
   - `open_image_triggered` → `_open_image`.
   - `quit_triggered` → `QApplication.quit`.
3. Create a `HotkeyManager` and connect
   `hotkey_pressed` → `_capture_screen`.
4. Call `hotkey_manager.start()` at launch and
   `hotkey_manager.stop()` on `aboutToQuit`.
5. Remove the in-app `Ctrl+Shift+T` shortcut from the
   menu bar (it is now handled globally by `pynput`).
   Keep `Ctrl+O` for Open Image in the menu.
6. Show a first-run dialog on macOS if the hotkey
   listener fails, guiding the user to grant
   Accessibility permissions in System Settings →
   Privacy & Security → Accessibility.

**Done when:** The full flow works: tray icon visible,
hotkey triggers capture from any app, window hides on
close, Quit terminates the process.

### Step 6 — Integration Testing and Polish

**Tasks:**

1. Manual smoke tests:
   - Launch app → tray icon appears.
   - Press global hotkey → capture overlay appears.
   - Right-click tray → Capture Screen works.
   - Right-click tray → Open Image works.
   - Close window → app keeps running in tray.
   - Tray → Quit exits the process.
2. Handle edge cases:
   - Hotkey pressed while capture overlay is already
     visible → ignore.
   - `pynput` not installed or permission denied →
     app still works via tray menu, with a warning.
   - Multiple rapid hotkey presses → debounce.
3. Update existing tests:
   - `test_main.py` — verify `MainWindow.closeEvent`
     hides instead of quitting.
4. Write `tests/test_tray.py`:
   - Test that `TrayIcon` creates with correct menu
     actions.
   - Test that signals are emitted on menu clicks.
5. Verify all Phase 1 and Phase 2 tests still pass.

**Done when:** Full tray + hotkey flow works end-to-end;
all tests pass.

## Acceptance Criteria

- [ ] `pynput` dependency added to `requirements.txt`.
- [ ] System tray icon appears with context menu
  (Capture Screen, Open Image, Show Window, Quit).
- [ ] Global hotkey (`Cmd+Shift+T` / `Ctrl+Shift+T`)
  triggers screen capture from any application.
- [ ] Closing the main window hides it; the app
  continues running in the system tray.
- [ ] "Quit" from the tray menu fully terminates the
  application.
- [ ] macOS Accessibility permission prompt is shown
  on first-run failure.
- [ ] All new and existing unit tests pass.
