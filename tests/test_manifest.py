"""Black-box tests for the release manifest and the deployment gate.

Builds into a temp copy of `data/` so the repo's real artifacts are never
mutated. Asserts the manifest records the artifact it wrote, and that the gate
rejects an artifact that drifted away from its manifest.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, REPO)
sys.path.insert(0, DATA_DIR)

from _pipeline import build_from_cache  # noqa: E402
from _verify_manifest import verify  # noqa: E402


@pytest.fixture
def built():
    tmp = tempfile.mkdtemp(prefix="manifest_")
    dest = os.path.join(tmp, "data")
    shutil.copytree(DATA_DIR, dest, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("model_registry.json", "axes_catalog.json", "processed.js", "manifest.json"):
        path = os.path.join(dest, name)
        if os.path.exists(path):
            os.remove(path)
    build_from_cache({"root": tmp})
    yield dest
    shutil.rmtree(tmp, ignore_errors=True)


def _read_manifest(dest):
    with open(os.path.join(dest, "manifest.json")) as f:
        return json.load(f)


def test_manifest_records_the_written_artifact(built):
    manifest = _read_manifest(built)
    with open(os.path.join(built, "processed.js"), "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()

    assert manifest["artifact"] == "processed.js"
    assert manifest["artifact_sha256"] == digest
    assert manifest["build_id"] == f"{manifest['generated']}@{digest[:12]}"
    assert manifest["model_count"] > 0
    assert {"AA", "OpenRouter"} <= set(manifest["sources"])
    assert manifest["sources"]["AA"] == "2026-09-24"


def test_gate_passes_on_a_fresh_build(built):
    assert verify(built).is_ok()


def test_gate_rejects_a_drifted_artifact(built):
    with open(os.path.join(built, "processed.js"), "a") as f:
        f.write("\n")

    result = verify(built)

    assert result.is_err()
    assert "does not match manifest" in result.error


def test_gate_rejects_a_missing_manifest(built):
    os.remove(os.path.join(built, "manifest.json"))

    result = verify(built)

    assert result.is_err()
    assert "manifest.json" in result.error


def test_committed_artifacts_match_their_manifest():
    result = verify(DATA_DIR)

    assert result.is_ok(), result.error if result.is_err() else ""
