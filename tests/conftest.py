"""Shared test fixtures for IMG2TXT."""

from pathlib import Path

import pytest


@pytest.fixture
def assets_dir() -> Path:
    """Return the path to the assets directory."""
    return Path(__file__).parent.parent / "assets"
