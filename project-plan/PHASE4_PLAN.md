# Phase 4 — Polish and Packaging

## Goal

Finish the remaining design-plan work: let users select a
region on a loaded (or already-captured) image in the
preview panel, close error-handling gaps that still leak
through to the user, and ship standalone binaries for
macOS, Windows, and Linux via PyInstaller and a GitHub
Actions release workflow.

## Prerequisites

- Phase 3 complete and all tests passing.
- `PyInstaller>=6.0` already listed in
  `requirements-dev.txt`.
- Tesseract OCR available on the host for local packaging
  tests (bundling is covered in Step 4).
- GitHub repository with Actions enabled and permission
  to publish Releases.

## Current State

Phases 1–3 already deliver file-open OCR, screenshot
capture with a fullscreen overlay, tray + global hotkey,
layout mode, and PR CI (lint + tests). The remaining
gaps against `DESIGN_PLAN.md` Phase 4 are:

- Preview `ImageLabel` only displays a scaled pixmap —
  there is no rubber-band selection on loaded images.
- `_load_image()` always OCRs the full file immediately.
- `Taskfile.yml` `build` is a one-liner that does not
  bundle `assets/` or Tesseract; `task clean` deletes
  `*.spec`.
- CI (`.github/workflows/ci.yml`) runs lint/tests only —
  there is no tag-triggered release build.
- Frozen-app paths (`assets/`, Tesseract binary) still
  assume a source checkout (`Path(__file__).parent`).
- Several edge cases are unguarded (see Step 2).

## Step-by-Step Implementation

### Step 1 — Region Selection on Loaded Images

Add a rubber-band selector on the preview image so Open
Image matches Design Plan Flow 2: optional region, full
image by default.

**Tasks:**

1. Extend `ImageLabel` in `src/preview.py` (or extract
   an `ImageSelector` widget) so the left preview panel
   supports mouse-drag selection:
   - Crosshair cursor when an image is loaded.
   - Rubber-band rectangle with a thin border.
   - Visible corner handles for resize after the first
     drag.
   - Escape (or a small "Clear selection" control)
     resets to the full image.
   - Ignore clicks when no image is loaded.
2. Map coordinates correctly:
   - Widget point → displayed (scaled, letterboxed)
     pixmap point → original-image pixel `QRect`.
   - Account for `KeepAspectRatio` letterboxing so the
     crop is not offset.
   - Reject selections smaller than 10 × 10 px (same
     threshold as `SelectionOverlay`).
3. Emit `region_selected(QRect)` in original-image
   pixels, and `selection_cleared()` when reset.
4. In `MainWindow`:
   - Keep `_current_image: Image.Image | None` for the
     full loaded/captured image (do not only store the
     cropped pixmap).
   - On Open Image: show the full image, OCR the full
     image immediately (current behaviour = default).
   - On `region_selected`: `crop_region(_current_image,
     rect)`, update the status bar, re-run OCR on the
     crop. Leave the full image visible with the overlay
     drawn — do not replace the preview image with the
     crop (user must be able to adjust the selection).
   - On `selection_cleared`: re-OCR the full image.
   - Screenshot capture still crops via the fullscreen
     overlay first; the preview selector then lets the
     user refine further.
5. Optional polish: an "OCR Selection" is not required
   if drag-release already re-runs OCR. Debounce rapid
   re-OCR (ignore a new drag while an OCR job is in
   flight, or cancel/replace the pending future).
6. Write `tests/test_selector.py` (preview selector,
   not the fullscreen overlay):
   - Coordinate mapping: a known pixmap size, widget
     size, and drag produces the expected original
     `QRect`.
   - Tiny selection is ignored.
   - Clear selection emits `selection_cleared`.
7. Extend `tests/test_preview.py` and `tests/test_main.py`
   to cover "load image → select region → OCR called
   with cropped image" using mocks.

**Done when:** Opening an image OCRs the full file;
dragging a rectangle on the preview re-OCRs only that
region; Escape restores full-image OCR; tests pass.

### Step 2 — Error Handling and Edge Cases

Close the remaining holes so the app never dies silently
and overlapping capture/OCR jobs cannot stack.

**Tasks:**

1. **Capture re-entrancy** — in `_capture_screen` /
   `_do_capture`, ignore the request if an overlay is
   already visible or a capture timer is pending.
   Same for the global hotkey (Phase 3 leftover).
2. **OCR in flight** — track `_ocr_busy`. A second
   `_run_ocr` while busy should either be dropped or
   replace the previous job; the UI must not apply a
   stale result after a newer crop.
3. **Image load** — wrap `Image.open(path)` in
   `_load_image` with `try/except (OSError,
   UnidentifiedImageError)` and show the existing
   "Invalid Image" dialog.
4. **Clipboard** — catch `pyperclip.PyperclipException`
   in `copy_and_notify` and surface a warning dialog
   (or return a `bool` that `PreviewWidget._on_copy`
   can show). Do not crash if the sound file is missing
   (already skipped).
5. **Executor lifecycle** — on `aboutToQuit`, call
   `window._executor.shutdown(wait=False)` so the
   process exits cleanly.
6. **Tray availability** — if
   `QSystemTrayIcon.isSystemTrayAvailable()` is false,
   keep `setQuitOnLastWindowClosed(True)` and skip
   creating the tray, so close actually quits.
7. **Crop bounds** — clamp `crop_region` to the image
   size so a mapped rect cannot go out of range.
8. Tests:
   - `test_main.py`: second capture while overlay
     active is a no-op; close-to-quit vs hide still
     holds when tray exists.
   - `test_clipboard.py`: copy failure does not raise.
   - `test_capture.py`: `crop_region` clamps overflow.

**Done when:** Overlay/hotkey spam is ignored, failed
loads/copies show dialogs, and the process exits
without hung worker threads.

### Step 3 — Frozen Resource Paths

Make assets and Tesseract resolvable both from source
and from a PyInstaller bundle.

**Tasks:**

1. Add `src/resources.py` with:

```python
def resource_path(*parts: str) -> Path:
    """Return an absolute path, honoring PyInstaller."""
```

   Use `sys._MEIPASS` when frozen, otherwise the
   project root (`Path(__file__).resolve().parent.parent`).

2. Point `src/clipboard.py` `ASSETS_DIR` and
   `src/tray.py` `_ICON_PATH` at `resource_path("assets", ...)`.
3. In `src/ocr.py` (or `resources.py`), if frozen and a
   bundled Tesseract exists, set
   `pytesseract.pytesseract.tesseract_cmd` and
   `TESSDATA_PREFIX` before calling Tesseract. If not
   bundled, keep the current system-PATH behaviour and
   existing `TesseractMissingError` message.
4. Unit-test `resource_path` with `sys.frozen` /
   `sys._MEIPASS` patched.

**Done when:** Sound, tray icon, and OCR still work
from `python -m src.main`, and the helper is ready for
the spec file in Step 4.

### Step 4 — PyInstaller Spec and Local Packaging

Replace the naive Taskfile one-liner with a committed
spec that bundles data files and, where practical,
Tesseract.

**Tasks:**

1. Add `img2txt.spec` at the repo root:
   - Entry: `src/main.py`.
   - `datas`: `assets/icon.png`, `assets/success.wav`.
   - `hiddenimports`: `PyQt6`, `pynput`, `mss`,
     `pytesseract`, `PIL`.
   - `--windowed` / `console=False`.
   - Prefer **onedir** over onefile for Tesseract
     shared libraries (onefile is acceptable if
     bundling is skipped on a given platform).
2. **Tesseract bundling** (best-effort per OS):
   - macOS: copy `tesseract` plus `eng.traineddata`
     (and required dylibs if the binary is not
     relocatable).
   - Windows: bundle `tesseract.exe` + `tessdata/eng.traineddata`.
   - Linux: document system `tesseract-ocr` as the
     default; optional bundle if CI can collect the
     binary and libs without breaking.
   - If bundling fails on a platform, the frozen app
     must still run against a system Tesseract and
     show the existing install instructions.
3. Update `Taskfile.yml`:
   - `build` runs `pyinstaller img2txt.spec`.
   - `clean` must **not** delete `img2txt.spec`
     (change `rm -rf build/ dist/ *.spec` to
     `rm -rf build/ dist/`).
4. Manual smoke test of the local binary:
   - Launch → tray icon and window appear.
   - Open Image → OCR + copy + sound.
   - Capture Screen → overlay → preview.
   - Quit from tray terminates.
5. Record known macOS entitlements (Accessibility,
   Screen Recording) in the README; codesigning is
   out of scope unless already configured.

**Done when:** `task build` produces a runnable binary
on the developer machine; `task clean` leaves the spec
file in place.

### Step 5 — GitHub Actions Release Workflow

Add a tag-triggered workflow that builds per platform
and publishes GitHub Release assets.

**Tasks:**

1. Create `.github/workflows/release.yml`:
   - Trigger: `push` of tags matching `v*`
     (e.g. `v0.1.0`).
   - Matrix: `macos-latest`, `windows-latest`,
     `ubuntu-latest`.
   - Steps: checkout, Python 3.13, install Tesseract
     (same as `ci.yml`), `pip install -r
     requirements-dev.txt`, `pyinstaller img2txt.spec`.
   - Upload artifacts named
     `img2txt-<os>-<arch>` (zip the onedir folder or
     the single executable).
   - A final job (or `softprops/action-gh-release`)
     attaches the three artifacts to the GitHub
     Release for that tag.
2. Keep `.github/workflows/ci.yml` for PR/main lint
   and tests — do not mix release builds into PR CI.
3. Document the release process in README:
   `git tag vX.Y.Z && git push --tags`.

**Done when:** Pushing a `v*` tag produces three
platform artifacts on a GitHub Release.

### Step 6 — Docs, Config Sync, and Integration Testing

**Tasks:**

1. Sync `pyproject.toml` `[project].dependencies`
   with `requirements.txt` (`mss`, `pynput` are
   missing from pyproject today).
2. Update `README.md`:
   - Project structure (tray, hotkey, capture,
     selector, packaging files).
   - Download/install from GitHub Releases.
   - Tesseract still required if not bundled.
   - macOS Accessibility + Screen Recording notes.
3. Tick Phase 4 boxes in `DESIGN_PLAN.md` only after
   the work lands (not as part of writing this plan).
4. Full regression: `task check` (lint, format, tests)
   on the development machine; confirm CI is green.

**Done when:** Docs match the tree, dependency files
agree, and all tests pass.

## Acceptance Criteria

- [ ] Preview image supports rubber-band region
  selection with coordinate mapping and handles.
- [ ] Open Image OCRs the full image by default;
  a preview selection re-OCRs only that crop.
- [ ] Escape / clear selection restores full-image
  OCR without replacing the displayed image.
- [ ] Capture and hotkey are ignored while an overlay
  is already active; OCR results cannot land out of
  order.
- [ ] Invalid images, clipboard failures, and missing
  Tesseract show user-facing dialogs, not tracebacks.
- [ ] Assets and optional bundled Tesseract resolve
  via a frozen-aware `resource_path`.
- [ ] `img2txt.spec` is committed; `task build`
  produces a binary; `task clean` does not delete
  the spec.
- [ ] Tag `v*` builds macOS, Windows, and Linux
  artifacts and attaches them to a GitHub Release.
- [ ] `pyproject.toml` and README match the current
  project; all new and existing tests pass.
