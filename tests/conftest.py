"""Shared fixtures for contract tests."""
import json, re, os, sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"


@pytest.fixture(scope="session")
def processed_js():
    """Parse processed.js and return model array."""
    with open(DATA / "processed.js") as f:
        content = f.read()
    m = re.match(r'window\.PROCESSED_DATA\s*=\s*(\[.*?\]);', content, re.DOTALL)
    assert m, "processed.js not parseable"
    return json.loads(m.group(1))


@pytest.fixture(scope="session")
def dashboard_html():
    """Read dashboard.html as string."""
    with open(REPO / "dashboard.html") as f:
        return f.read()


@pytest.fixture(scope="session")
def shared_js():
    """Read viz/_shared.js as string."""
    with open(REPO / "viz" / "_shared.js") as f:
        return f.read()
