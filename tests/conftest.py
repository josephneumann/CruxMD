"""Pytest configuration and fixtures for CruxMD tests."""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthea"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_bundle() -> dict:
    """Load first patient bundle fixture."""
    with open(FIXTURES_DIR / "patient_bundle_1.json") as f:
        return json.load(f)


@pytest.fixture
def all_bundles() -> list[dict]:
    """Load all patient bundle fixtures."""
    bundles = []
    for path in sorted(FIXTURES_DIR.glob("patient_bundle_*.json")):
        with open(path) as f:
            bundles.append(json.load(f))
    return bundles
