# IMG2TXT Design Plan

## Overview

IMG2TXT is a cross-platform desktop application that extracts
text from images and copies it to the clipboard. It runs offline,
lives in the system tray, and provides a global hotkey for
instant screenshot-to-text capture.

## Technology Stack

### Recommendation — Python

Python is the clear choice for this project because:

- **Tesseract OCR** has mature Python bindings
  (`pytesseract`) — the best free offline OCR engine.
- **PyQt6** provides a rich, native-feeling GUI with
  system tray support on all three platforms.
- **PyAutoGUI / mss** enable cross-platform screenshot
  capture.
- **PyInstaller** produces standalone binaries for
  macOS, Windows, and Linux from a single codebase.
- Go lacks mature GUI and OCR library support by
  comparison.

| Component        | Library / Tool              |
| ---------------- | --------------------------- |
| Language         | Python 3.13+                |
| GUI framework    | PyQt6                       |
| OCR engine       | Tesseract OCR + pytesseract |
| Screenshot       | mss (cross-platform)        |
| Clipboard        | pyperclip                   |
| Global hotkey    | pynput                      |
| Audio feedback   | playsound / QSound          |
| Packaging        | PyInstaller                 |

## Architecture

```text
┌─────────────────────────────────────────────┐
│                System Tray                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Capture  │  │ Open File│  │   Quit   │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │   Main Controller   │
        │  (event routing)    │
        └──┬─────┬────────┬───┘
           │     │        │
     ┌─────▼┐ ┌──▼────┐ ┌─▼──────────┐
     │Screen│ │ File  │ │  Preview   │
     │Capture│ │Picker │ │  Window    │
     └──┬───┘ └──┬────┘ │            │
        │        │      │ ┌────────┐ │
        └────┬───┘      │ │ Image  │ │
             │          │ │ Panel  │ │
        ┌────▼────┐     │ ├────────┤ │
        │Selection│     │ │ Text   │ │
        │ Overlay │     │ │ Panel  │ │
        └────┬────┘     │ └────────┘ │
             │          └──────┬─────┘
        ┌────▼────┐            │
        │   OCR   │◄───────────┘
        │ Engine  │
        └────┬────┘
             │
        ┌────▼────┐
        │Clipboard│──► notification sound
        └─────────┘
```

## Core Modules

### Module 1 — System Tray (`tray.py`)

- App icon in system tray / macOS menu bar.
- Context menu: **Capture Screen**, **Open Image**,
  **Quit**.
- Keeps the app running in the background.

### Module 2 — Global Hotkey (`hotkey.py`)

- Registers a system-wide shortcut
  (default: `Ctrl+Shift+T`, `Cmd+Shift+T` on macOS).
- Triggers the screenshot capture flow from any context.

### Module 3 — Screenshot Capture (`capture.py`)

- Uses `mss` to grab a full-screen screenshot.
- Displays a translucent fullscreen overlay.
- User drags a rectangle to select the region of
  interest.
- Crops the image to the selected area.

### Module 4 — File Picker (`picker.py`)

- Native file dialog via `QFileDialog`.
- Accepts PNG, JPG, JPEG, BMP, TIFF, WEBP.

### Module 5 — Selection Overlay (`selector.py`)

- Draggable rectangle overlay on the loaded image.
- Lets the user refine which part of an image to OCR.
- Rubber-band selection with visible handles.

### Module 6 — OCR Engine (`ocr.py`)

- Wraps `pytesseract.image_to_string()`.
- Accepts a PIL Image, returns extracted text.
- English language pack only (initial version).
- Runs in a background thread to keep the UI
  responsive.

### Module 7 — Preview Window (`preview.py`)

- Split-panel layout:
  - **Left**: image preview with selection overlay.
  - **Right**: extracted text (read-only display).
- "Copy to Clipboard" button.
- Displays the captured or loaded image alongside
  the OCR result.

### Module 8 — Clipboard & Feedback (`clipboard.py`)

- Copies extracted text to the system clipboard.
- Plays a short notification sound on success.

## User Flows

### Flow 1 — Screenshot Capture

1. User presses global hotkey (`Ctrl+Shift+T`).
2. Screen dims with a translucent overlay.
3. User drags a rectangle over the desired area.
4. Preview window opens with the captured region and
   extracted text.
5. User clicks "Copy to Clipboard".
6. Text is copied; notification sound plays.

### Flow 2 — File Picker

1. User right-clicks the tray icon → **Open Image**.
2. File dialog opens; user selects an image.
3. Preview window opens with the image.
4. User drags a rectangle to select a region
   (optional — defaults to full image).
5. OCR runs on the selected region.

## Project Structure

```text
img2txt/
├── src/
│   ├── __init__.py
│   ├── main.py          # entry point
│   ├── tray.py           # system tray integration
│   ├── hotkey.py          # global hotkey listener
│   ├── capture.py         # screenshot capture
│   ├── picker.py          # file picker dialog
│   ├── selector.py        # rectangle selection overlay
│   ├── ocr.py             # tesseract wrapper
│   ├── preview.py         # preview window (image + text)
│   └── clipboard.py       # clipboard + sound feedback
├── assets/
│   ├── icon.png           # tray icon
│   └── success.wav        # notification sound
├── tests/
│   ├── test_ocr.py
│   ├── test_capture.py
│   └── test_clipboard.py
├── requirements.txt
├── DESIGN_PLAN.md
├── README.md
├── LICENSE
└── img2txt.spec           # PyInstaller spec file
```

## Packaging & Distribution

- **PyInstaller** produces a single executable per
  platform.
- Tesseract OCR engine and English language data
  (`eng.traineddata`) are bundled inside the binary.
- CI/CD via GitHub Actions builds binaries for macOS,
  Windows, and Linux on each release tag.

## Development Milestones

### Phase 1 — Core OCR (MVP)

- [ ] Project scaffolding and dependency setup.
- [ ] OCR engine wrapper (`ocr.py`).
- [ ] File picker and basic preview window.
- [ ] Copy to clipboard with sound feedback.

### Phase 2 — Screenshot Capture

- [ ] Full-screen screenshot via `mss`.
- [ ] Translucent overlay with rectangle selection.
- [ ] Pipe captured region into OCR and preview.

### Phase 3 — System Tray and Global Hotkey

- [ ] System tray icon with context menu.
- [ ] Global hotkey registration.
- [ ] Background process lifecycle management.

### Phase 4 — Polish and Packaging

- [ ] Rectangle selection on loaded images.
- [ ] Error handling and edge cases.
- [ ] PyInstaller packaging and testing on all three
  platforms.
- [ ] GitHub Actions CI/CD for release builds.

## Dependencies

```text
pytesseract>=0.3.10
PyQt6>=6.5
mss>=9.0
pyperclip>=1.8
pynput>=1.7
Pillow>=10.0
playsound>=1.3
PyInstaller>=6.0  # dev dependency
```

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Tesseract bundling increases binary size (~30 MB) | Acceptable trade-off for offline support |
| Global hotkey conflicts with other apps | Make the shortcut user-configurable |
| pynput requires accessibility permissions on macOS | Show a first-run prompt guiding the user |
| PyQt6 binary size is large (~80 MB) | Consider PySide6 as a lighter alternative |