# Implementation Plan — Dual-mode OCR (Plain + Layout-preserving)

**GitHub Issue:** [#14 — feat: update tool to respect tabs & spaces](https://github.com/emylincon/img2txt/issues/14)

## Problem

Currently `extract_text()` calls `pytesseract.image_to_string()` followed by `.strip()`, which collapses all spatial layout (indentation, multiple spaces, tabs). This makes the tool unsuitable for capturing code snippets, terminal output, or any structured text.

## Solution

Add a user-facing toggle that switches between two OCR strategies:

| Mode   | Strategy                                | Best for                    |
| ------ | --------------------------------------- | --------------------------- |
| Plain  | `image_to_string` + `.strip()` (current)| Prose, paragraphs           |
| Layout | `image_to_data` + spatial reconstruction| Code, terminal output, tables|

## Data Flow

```
User toggles mode (Tray menu / File menu)
         │
         ▼
  MainWindow stores `_preserve_layout: bool`
         │
         ▼
  _run_ocr(image) passes flag
         │
         ├─ False → pytesseract.image_to_string (current behavior)
         └─ True  → pytesseract.image_to_data → spatial reconstruction
                          │
                          ▼
                   _reconstruct_layout(data)
                   group by line, compute leading spaces from x-offset
         │
         ▼
  Signal: _ocr_signals.finished(text)
         │
         ▼
  PreviewWidget.set_text(text) + monospace font when layout mode
```

## File-by-File Changes

### 1. `src/ocr.py` — Core OCR logic

- Add a `preserve_layout: bool = False` parameter to `extract_text()`.
- When `preserve_layout=False`: keep current behaviour (`image_to_string` + `.strip()`).
- When `preserve_layout=True`:
  1. Call `pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)`.
  2. Pass the result to a new private function `_reconstruct_layout(data) -> str`.
- **`_reconstruct_layout(data)`** algorithm:
  1. Zip `data["line_num"]`, `data["left"]`, `data["text"]`, `data["conf"]` together.
  2. Filter out entries with `conf < 0` or empty text.
  3. Group words by `(block_num, par_num, line_num)`.
  4. Determine `char_width` — estimate average character pixel width from the data (`width / len(text)` averaged across confident words).
  5. For each line:
     - Compute leading spaces: `first_word_left // char_width`.
     - Compute inter-word gaps: `(current_left - previous_right) // char_width` spaces between each word.
  6. Join lines with `\n`. Strip only trailing whitespace from the final result.

### 2. `src/main.py` — Thread the setting through

- Add instance attribute `self._preserve_layout: bool = False`.
- Add `_toggle_layout_mode()` method that flips the bool and updates the menu check state.
- Update `_setup_menu()`:
  - Add a checkable **"Preserve Layout"** action under the File menu (above the separator before Quit).
  - Connect it to `_toggle_layout_mode()`.
- Update `_run_ocr(self, image)`:
  - Read `self._preserve_layout` and pass it to `extract_text(image, preserve_layout=...)`.
- Update `_on_ocr_done(self, text)`:
  - If `self._preserve_layout` is `True`, call `self.preview.set_monospace(True)` before setting text.
  - Otherwise call `self.preview.set_monospace(False)`.

### 3. `src/tray.py` — Tray menu toggle

- Add a new signal: `layout_mode_toggled = pyqtSignal(bool)`.
- In `_build_menu()`:
  - Add a checkable **"Preserve Layout"** action (between "Open Image…" and the separator).
  - Connect its `toggled` signal to `layout_mode_toggled.emit`.
- Add a public method `set_layout_mode(checked: bool)` to programmatically sync the check state (called from `MainWindow` so tray and menu stay in sync).

### 4. `src/preview.py` — Monospace font support

- Add a `set_monospace(enabled: bool)` method to `PreviewWidget`:
  - When `True`: set `QTextEdit` font to a monospace family (e.g. `QFont("Menlo", 12)` on macOS, `"Consolas"` on Windows, `"Monospace"` on Linux) and disable word wrap.
  - When `False`: restore the default proportional font and re-enable word wrap.

### 5. `src/main.py` — Wire tray ↔ window sync

In the `main()` function:
- Connect `tray.layout_mode_toggled` → `window._set_layout_mode`.
- Connect `window` layout mode change → `tray.set_layout_mode` (to keep both in sync).

### 6. `tests/test_ocr.py` — Unit tests for new OCR logic

- **`test_extract_text_preserve_layout_flag`**: mock `image_to_data`, verify `_reconstruct_layout` is called when `preserve_layout=True`.
- **`test_reconstruct_layout_indentation`**: feed synthetic `image_to_data` dict with known `left`/`width` values, assert correct leading spaces.
- **`test_reconstruct_layout_inter_word_gaps`**: assert multiple spaces between far-apart words.
- **`test_reconstruct_layout_multiline`**: assert lines are separated by `\n` and each has correct indentation.
- **`test_extract_text_plain_mode_unchanged`**: confirm `preserve_layout=False` still calls `image_to_string` and strips.

### 7. `tests/test_tray.py` — Tray menu tests

- **`test_preserve_layout_action_exists`**: assert the "Preserve Layout" action is in the tray context menu.
- **`test_layout_mode_signal_emitted`**: toggle the action, assert `layout_mode_toggled` signal fires with correct bool.

### 8. `tests/test_main.py` — MainWindow integration tests

- **`test_preserve_layout_menu_action`**: assert the "Preserve Layout" action exists in the File menu.
- **`test_layout_mode_default_false`**: assert `window._preserve_layout` is `False` on init.

## Implementation Order

1. `src/ocr.py` — add `preserve_layout` param + `_reconstruct_layout()`.
2. `tests/test_ocr.py` — add unit tests, run and verify.
3. `src/preview.py` — add `set_monospace()` method.
4. `src/tray.py` — add toggle action + signal.
5. `tests/test_tray.py` — add tray toggle tests, run and verify.
6. `src/main.py` — wire everything together (menu, state, tray sync).
7. `tests/test_main.py` — add integration tests, run and verify.
8. Manual end-to-end test with a code screenshot.

## No New Dependencies

All changes use `pytesseract.image_to_data` which is already available via the existing `pytesseract` dependency. No new packages required.
