"""Black-box determinism test: full pipeline build is byte-stable across runs.

Runs the real `build_from_cache` pipeline (registry -> axes -> dashboard) twice
against the real source fixtures, and asserts the three generated artifacts
(model_registry.json, axes_catalog.json, processed.js) are byte-identical
between runs.

This is the input->output contract the user asked for: same source data in,
same bytes out, no drift. No implementation spying — we only compare the
produced files. Uses `build_from_cache` (skips the network pull stage) so the
test is offline and deterministic.

Fixtures are copied into a temp dir per run so the repo's real artifacts are
never mutated.
"""
import sys, os, shutil, hashlib, tempfile
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, DATA_DIR)

from _pipeline import build_from_cache  # noqa: E402


def _run_pipeline_to_tmp():
    """Copy real `data/` into a temp dir, run build_from_cache, return the dir."""
    tmp = tempfile.mkdtemp(prefix="pipeline_det_")
    dest = os.path.join(tmp, "data")
    shutil.copytree(DATA_DIR, dest, ignore=shutil.ignore_patterns("__pycache__"))
    ctx = {"root": tmp}
    build_from_cache(ctx)
    return dest


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _artifact_hashes(dest):
    return {
        name: _sha256(os.path.join(dest, name))
        for name in ("model_registry.json", "axes_catalog.json", "processed.js")
    }


def test_full_pipeline_is_deterministic():
    run1 = _run_pipeline_to_tmp()
    hashes1 = _artifact_hashes(run1)

    run2 = _run_pipeline_to_tmp()
    hashes2 = _artifact_hashes(run2)

    for name in ("model_registry.json", "axes_catalog.json", "processed.js"):
        assert hashes1[name] == hashes2[name], (
            f"{name} differs between two identical pipeline runs "
            f"(run1={hashes1[name][:12]} run2={hashes2[name][:12]})"
        )

    for d in (run1, run2):
        shutil.rmtree(d, ignore_errors=True)


def test_full_pipeline_artifacts_are_nonempty():
    """Sanity: a real build produces populated artifacts (not just stable-empty)."""
    run = _run_pipeline_to_tmp()
    reg = _sha256(os.path.join(run, "model_registry.json"))
    axes = _sha256(os.path.join(run, "axes_catalog.json"))
    proc = _sha256(os.path.join(run, "processed.js"))

    assert reg != hashlib.sha256(b"").hexdigest()
    assert axes != hashlib.sha256(b"").hexdigest()
    assert proc != hashlib.sha256(b"").hexdigest()

    shutil.rmtree(run, ignore_errors=True)
