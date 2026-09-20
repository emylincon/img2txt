# IMG2TXT

Extract and copy text from images, screenshots, and
scanned documents.

## Features

- **Image to text** — pull text from any photo,
  screenshot, or scanned document.
- **Screenshot to text** — capture text from articles,
  social posts, dashboards, and error messages.
- **Area selection** — drag a rectangle to grab text
  from a specific region.
- **Editable preview** — edit extracted text directly in
  the preview box to fix OCR mistakes before copying.
- **Simple interface** — intuitive split-panel preview
  with one-click copy.
- **Layout mode** — preserve indentation and spacing
  when capturing code, terminal output, or YAML.
  Configurable indent width (2, 4, or 8 spaces).
- **Offline** — runs entirely on your machine using
  Tesseract OCR.
- **System tray + hotkey** — capture from the tray or
  with a global shortcut (Ctrl+Shift+2 / Cmd+Shift+2).

## Download

Pre-built binaries for macOS, Windows, and Linux are
attached to [GitHub Releases][releases]. Unzip the
platform archive and run `img2txt`.

Tesseract is bundled when the build machine has it
installed; otherwise install Tesseract separately
(see below).

## Prerequisites

- Python 3.13+
- [Tesseract OCR][tesseract] installed on your system

### Installing Tesseract

```bash
# macOS
brew install tesseract

# Ubuntu / Debian
sudo apt install tesseract-ocr

# Windows (via chocolatey)
choco install tesseract
```

### macOS permissions

The frozen (and source) app needs two macOS TCC grants:

- **Accessibility** — global hotkey (`pynput`) and
  simulating input. Grant this under
  System Settings → Privacy & Security → Accessibility.
- **Screen Recording** — screenshot capture via `mss`.
  Grant this under System Settings → Privacy & Security
  → Screen Recording.

Codesigning and notarization are out of scope; unsigned
builds may prompt on first launch.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/img2txt.git
cd img2txt

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python -m src.main
```

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Or run lint + format check + tests together
task check
```

## Packaging

```bash
# Build a windowed onedir bundle into dist/img2txt/
task build

# Remove build/ and dist/ (keeps img2txt.spec)
task clean
```

The committed `img2txt.spec` packs `assets/` and, when
Tesseract is on the build machine PATH, copies the
binary plus `eng.traineddata`. Linux releases still
work against a system `tesseract-ocr` install if
bundling is skipped.

## Releases

Push a version tag to trigger
`.github/workflows/release.yml`, which builds macOS,
Windows, and Linux artifacts and attaches them to a
GitHub Release:

```bash
git tag v0.1.0
git push --tags
```

## Layout Mode

Layout mode reconstructs indentation and spacing from
the OCR bounding-box data instead of returning collapsed
plain text. This is useful for code snippets, terminal
output, YAML, and any structured text.

### How to enable

Toggle **Preserve Layout** from either:

- **File menu** → Preserve Layout
- **System tray** → Preserve Layout

When enabled, the text preview switches to a monospace
font and disables word wrap so alignment is preserved.

### Indent Width

You can choose the indent width (2, 4, or 8 spaces)
from the **Indent Width** submenu, which appears in both
the File menu and the system tray menu. The submenu is
only enabled when Preserve Layout is active.

The indent width controls how leading spaces are
normalised:

1. **Baseline subtraction** — the leftmost text in the
   image maps to column 0.
2. **Snap to grid** — leading spaces are rounded to the
   nearest multiple of the chosen indent width.
3. **Max-increase clamp** — a line's indentation can
   increase by at most one indent level relative to the
   previous line. Decreases are unrestricted.

## Project Structure

```text
img2txt/
├── src/
│   ├── main.py
│   ├── ocr.py
│   ├── picker.py
│   ├── preview.py
│   ├── clipboard.py
│   ├── capture.py
│   ├── selector.py
│   ├── tray.py
│   ├── hotkey.py
│   └── resources.py
├── assets/
├── tests/
├── project-plan/
├── .github/workflows/
│   ├── ci.yml
│   └── release.yml
├── img2txt.spec
├── Taskfile.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

## License

MIT — see [LICENSE](LICENSE) for details.

[tesseract]: https://github.com/tesseract-ocr/tesseract
[releases]: https://github.com/your-username/img2txt/releases
