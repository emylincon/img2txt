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
- **Simple interface** — intuitive split-panel preview
  with one-click copy.
- **Layout mode** — preserve indentation and spacing
  when capturing code, terminal output, or YAML.
  Configurable indent width (2, 4, or 8 spaces).
- **Offline** — runs entirely on your machine using
  Tesseract OCR.

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
│   ├── __init__.py
│   ├── main.py
│   ├── ocr.py
│   ├── picker.py
│   ├── preview.py
│   └── clipboard.py
├── assets/
├── tests/
├── project-plan/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

## License

MIT — see [LICENSE](LICENSE) for details.

[tesseract]: https://github.com/tesseract-ocr/tesseract
