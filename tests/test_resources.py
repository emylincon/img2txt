"""Tests for frozen-aware resource path resolution."""

from pathlib import Path
from unittest.mock import patch

from src.resources import configure_tesseract, resource_path


class TestResourcePath:
    """Tests for resource_path()."""

    def test_source_checkout_uses_project_root(self):
        """Unfrozen paths resolve from the repo root."""
        result = resource_path("assets", "icon.png")
        expected = (
            Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        )
        assert result == expected

    def test_frozen_uses_meipass(self, tmp_path):
        """Frozen apps resolve under sys._MEIPASS."""
        with (
            patch("src.resources.sys") as mock_sys,
        ):
            mock_sys.frozen = True
            mock_sys._MEIPASS = str(tmp_path)
            result = resource_path("assets", "success.wav")
        assert result == tmp_path / "assets" / "success.wav"


class TestConfigureTesseract:
    """Tests for configure_tesseract()."""

    def test_noop_when_not_frozen(self):
        """Source runs leave pytesseract.tesseract_cmd untouched."""
        with patch("src.resources.sys") as mock_sys:
            mock_sys.frozen = False
            configure_tesseract()

    def test_sets_cmd_when_bundled_binary_exists(self, tmp_path):
        """Frozen apps with a bundled binary set tesseract_cmd."""
        bundled = tmp_path / "tesseract"
        bundled.mkdir()
        exe = bundled / "tesseract"
        exe.write_text("")
        tessdata = bundled / "tessdata"
        tessdata.mkdir()

        with (
            patch("src.resources.sys") as mock_sys,
            patch("src.resources.os.environ", {}) as environ,
            patch("pytesseract.pytesseract") as mock_pt,
        ):
            mock_sys.frozen = True
            mock_sys.platform = "darwin"
            mock_sys._MEIPASS = str(tmp_path)
            configure_tesseract()

        assert mock_pt.tesseract_cmd == str(exe)
        assert environ["TESSDATA_PREFIX"] == str(bundled)
