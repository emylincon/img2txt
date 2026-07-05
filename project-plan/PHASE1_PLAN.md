# Phase 1 — Core OCR (MVP) Implementation Plan

## Goal

Deliver a working desktop app that opens an image via
a file picker, extracts text with Tesseract OCR, displays
the image and text side by side, and copies the text to
the clipboard with a notification sound.

## Prerequisites

- Python 3.13+ installed.
- Tesseract OCR installed on the host machine
  (bundling comes in Phase 4).
- A virtual environment for dependency isolation.

## Step-by-Step Implementation

### Step 1 — Project Scaffolding

Create the directory structure, virtual environment,
and install dependencies.

**Tasks:**

1. Create `src/` directory with `__init__.py`.
2. Create `assets/` directory.
3. Create `tests/` directory.
4. Create `requirements.txt` with Phase 1 deps:

```text
pytesseract>=0.3.10
PyQt6>=6.5
pyperclip>=1.8
Pillow>=10.0
playsound>=1.3
```

5. Create and activate a virtual environment.
6. Install dependencies via `pip install -r
   requirements.txt`.
7. Add a short notification sound file at
   `assets/success.wav`.
8. Create `src/main.py` with a minimal PyQt6
   application that opens an empty window.
9. Verify the app launches: `python src/main.py`.

**Done when:** Empty PyQt6 window opens and closes
cleanly.

### Step 2 — OCR Engine Wrapper (`src/ocr.py`)

Wrap Tesseract in a clean interface.

**Tasks:**

1. Create `src/ocr.py` with a function:

```python
def extract_text(image: PIL.Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image.
    Returns the extracted text string.
    """
```

2. Handle errors gracefully (Tesseract not found,
   invalid image).
3. Run OCR in a background thread using
   `QThread` or `concurrent.futures` to avoid
   blocking the UI.
4. Write `tests/test_ocr.py`:
   - Test with a known image containing text.
   - Test with a blank image (returns empty string).
   - Test with an invalid input (raises error).

**Done when:** `pytest tests/test_ocr.py` passes.

### Step 3 — File Picker (`src/picker.py`)

Allow users to select an image file.

**Tasks:**

1. Create `src/picker.py` with a function:

```python
def open_image_dialog(
    parent: QWidget,
) -> Optional[str]:
    """Show a file dialog filtered to image types.
    Returns the selected file path or None.
    """
```

2. Filter to: `*.png *.jpg *.jpeg *.bmp *.tiff *.webp`.
3. Integrate into `main.py` — add an "Open Image"
   button that calls the picker.

**Done when:** Clicking the button opens a native file
dialog and returns the selected path.

### Step 4 — Preview Window (`src/preview.py`)

Display the image and extracted text side by side.

**Tasks:**

1. Create `src/preview.py` with a `PreviewWindow`
   class (extends `QWidget` or `QMainWindow`).
2. Layout — horizontal splitter:
   - **Left panel**: `QLabel` displaying the image,
     scaled to fit.
   - **Right panel**: `QTextEdit` (read-only) showing
     the extracted text.
3. Add a "Copy to Clipboard" button below the text
   panel.
4. Wire the flow in `main.py`:
   - User clicks "Open Image".
   - Image loads into the left panel.
   - OCR runs in background → text appears in the
     right panel.
   - "Copy to Clipboard" button is enabled.

**Done when:** Opening an image shows it alongside the
extracted text in a split view.

### Step 5 — Clipboard and Sound Feedback

Copy text and play a sound.

**Tasks:**

1. Create `src/clipboard.py` with:

```python
def copy_and_notify(text: str) -> None:
    """Copy text to clipboard and play a sound."""
```

2. Use `pyperclip.copy()` for clipboard access.
3. Play `assets/success.wav` using `playsound` or
   `QSoundEffect` (PyQt6 built-in, more reliable
   cross-platform).
4. Wire the "Copy to Clipboard" button in
   `preview.py` to call `copy_and_notify()`.
5. Write `tests/test_clipboard.py`:
   - Test that text is placed on the clipboard.

**Done when:** Clicking "Copy to Clipboard" copies the
text and plays the notification sound.

### Step 6 — Integration and Polish

Connect all modules and handle edge cases.

**Tasks:**

1. Wire the full flow end-to-end in `main.py`:
   `Open → Load → OCR → Preview → Copy`.
2. Add a loading spinner or "Extracting text…" label
   while OCR runs.
3. Handle edge cases:
   - No text found → show "No text detected" message.
   - File dialog cancelled → do nothing.
   - Tesseract not installed → show a clear error
     dialog with install instructions.
4. Add a menu bar with **File → Open Image** and
   **File → Quit**.
5. Set the window title to "IMG2TXT" and add an
   app icon.
6. Run a manual smoke test on macOS (and Windows /
   Linux if available).

**Done when:** The full MVP flow works end-to-end
with no crashes or unhandled errors.

## Acceptance Criteria

- [ ] App launches with a PyQt6 window.
- [ ] "Open Image" loads an image via file picker.
- [ ] Image displays in the left panel.
- [ ] OCR extracts text and displays it in the right
  panel.
- [ ] "Copy to Clipboard" copies text and plays a
  sound.
- [ ] Errors (no Tesseract, no text, bad file) show
  user-friendly messages.
- [ ] All unit tests pass (`pytest tests/`).
