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
