# Phase 2 — Screenshot Capture Implementation Plan

## Goal

Add the ability to capture a region of the screen via
a screenshot, select a rectangular area through a
translucent overlay, and pipe the cropped image into the
existing OCR and preview pipeline from Phase 1.

## Prerequisites

- Phase 1 complete and all tests passing.
- `mss` library installed (`mss>=9.0`).
- Multi-monitor awareness is desirable but single
  primary monitor is acceptable for the initial pass.

## Step-by-Step Implementation

### Step 1 — Add `mss` Dependency

Install `mss` and update `requirements.txt`.

**Tasks:**

1. Run `pip install mss>=9.0`.
2. Add `mss>=9.0` to `requirements.txt`.
3. Verify import: `python -c "import mss; print(mss)"`.

**Done when:** `mss` imports without error.

### Step 2 — Screenshot Capture Module (`src/capture.py`)

Take a full-screen screenshot and return it as a PIL
Image.

**Tasks:**

1. Create `src/capture.py` with a function:

```python
def take_screenshot() -> PIL.Image.Image:
    """Capture the entire primary monitor.
    Returns a PIL Image of the full screen.
    """
```

2. Use `mss.mss()` context manager to grab the primary
   monitor via `sct.grab(sct.monitors[1])`.
3. Convert the `mss` `ScreenShot` object to a PIL Image
   using `Image.frombytes()`.
4. Write `tests/test_capture.py`:
   - Test that `take_screenshot()` returns a PIL Image.
   - Test that the returned image has non-zero dimensions.

**Done when:** `pytest tests/test_capture.py` passes.

### Step 3 — Selection Overlay (`src/selector.py`)

Display the screenshot as a fullscreen translucent
overlay and let the user drag a rectangle to select a
region.

**Tasks:**

1. Create `src/selector.py` with a `SelectionOverlay`
   class (extends `QWidget`):
   - Receives a `QPixmap` of the screenshot.
   - Shows as a frameless fullscreen window.
   - Dims the image with a semi-transparent dark wash.
   - On mouse press: record start point.
   - On mouse move: draw a rubber-band rectangle.
   - On mouse release: emit a signal with the selected
     `QRect`.
   - On `Escape` key: cancel and close.
2. The selected rectangle should highlight the chosen
   region (clear the dark wash inside the selection).
3. Draw a thin border around the selection rectangle
   for visibility.
4. Emit a custom signal `region_selected(QRect)` when
   the user releases the mouse.
5. Emit `cancelled()` when the user presses `Escape`.
6. Add a crosshair cursor while the overlay is active.

**Done when:** Launching the overlay over a screenshot
lets the user drag a rectangle; closing emits the
correct `QRect` coordinates.

### Step 4 — Crop and Pipe to OCR

Connect the captured screenshot and selected region to
the existing OCR and preview pipeline.

**Tasks:**

1. Add a `crop_region()` function in `capture.py`:

```python
def crop_region(
    image: PIL.Image.Image,
    rect: QRect,
) -> PIL.Image.Image:
    """Crop a PIL Image to the given QRect."""
```

2. In `MainWindow` (`src/main.py`), add a new method
   `_capture_screen()`:
   - Call `take_screenshot()`.
   - Convert the PIL Image to a `QPixmap` and pass it
     to `SelectionOverlay`.
   - Connect `region_selected` to a handler that crops
     the image, sends it to OCR, and opens the preview.
3. Add a **Capture Screen** action to the File menu
   (shortcut: `Ctrl+Shift+T`).
4. Reuse the existing `_run_ocr` / `_on_ocr_done` /
   `_on_ocr_error` pipeline — pass the cropped PIL
   Image directly instead of a file path.
   - Refactor `_run_ocr` to accept either a file path
     or a PIL Image.

**Done when:** Selecting "Capture Screen" takes a
screenshot, shows the overlay, and after selection the
cropped region appears in the preview with OCR text.

### Step 5 — Integration Testing and Polish

**Tasks:**

1. Manual smoke test: full capture → select → OCR →
   copy flow.
2. Handle edge cases:
   - Zero-area selection (user clicks without dragging)
     → ignore or show a message.
   - Very small selection → proceed normally; Tesseract
     handles small images.
   - Multi-monitor: capture the primary monitor only.
3. Ensure the overlay closes cleanly on cancel and on
   successful selection.
4. Update `tests/test_capture.py` with:
   - Test for `crop_region()` with a known rect.
   - Test that cropping returns correct dimensions.
5. Verify all existing Phase 1 tests still pass.

**Done when:** Full capture flow works end-to-end with
no crashes; all tests pass.

## Acceptance Criteria

- [ ] `mss` dependency added to `requirements.txt`.
- [ ] `take_screenshot()` returns a full-screen PIL
  Image.
- [ ] Fullscreen translucent overlay appears on capture.
- [ ] User can drag a rectangle to select a region.
- [ ] Pressing Escape cancels the capture.
- [ ] Cropped region is piped into OCR and displayed in
  the preview window.
- [ ] "Capture Screen" menu action works (Ctrl+Shift+T).
- [ ] All new and existing unit tests pass.
