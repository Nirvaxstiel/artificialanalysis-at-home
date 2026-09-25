"""Black-box tests for the failed-refresh signal.

A refresh that fails must not look like a refresh that succeeded. The pull stage
records the outcome, the registry carries it into source meta, and the artifact
that ships keeps it.
"""
import json
import os
import shutil
import sys
import tempfile
from unittest import mock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, REPO)
sys.path.insert(0, DATA_DIR)

import data._build_registry as br  # noqa: E402
import _pull_sources as ps  # noqa: E402
from _pipeline import build_from_cache  # noqa: E402


def _patch_pulls(livebench, openllm, openrouter, catalog, dirac):
    return mock.patch.multiple(
        ps,
        pull_livebench=mock.MagicMock(return_value=livebench),
        pull_openllm=mock.MagicMock(return_value=openllm),
        pull_openrouter=mock.MagicMock(return_value=openrouter),
        pull_aa_public_model_catalog=mock.MagicMock(return_value=catalog),
        pull_dirac=mock.MagicMock(return_value=dirac),
    )


def _status_file(tmp_path):
    return tmp_path / "data" / "sources" / ps.PULL_STATUS_FILE


def test_run_writes_the_refresh_outcome(tmp_path):
    with _patch_pulls(
        ps.err("lb down"), ps.ok({"rows": 0}), ps.ok({"models": 0}),
        ps.ok({"models": 0}), ps.ok({"rows": 0}),
    ):
        result = ps.run({"root": str(tmp_path)})

    assert result.is_ok()
    status = json.loads(_status_file(tmp_path).read_text(encoding="utf-8"))
    assert status["failed"] == {"livebench": "lb down"}
    assert "openrouter" in status["ok"]
    assert status["checked_at"]


def test_run_records_the_outcome_when_every_source_fails(tmp_path):
    with _patch_pulls(
        ps.err("lb down"), ps.err("ol down"), ps.err("or down"),
        ps.err("aa down"), ps.err("dirac down"),
    ):
        result = ps.run({"root": str(tmp_path)})

    assert result.is_err()
    status = json.loads(_status_file(tmp_path).read_text(encoding="utf-8"))
    assert set(status["failed"]) == {"livebench", "openllm", "openrouter", "aa_public_catalog", "dirac"}
    assert status["ok"] == []


def test_source_meta_marks_a_failed_refresh(tmp_path):
    (tmp_path / ps.PULL_STATUS_FILE).write_text(
        json.dumps({"checked_at": "2026-09-25T00:00:00Z", "ok": ["livebench"], "failed": {"openrouter": "or down"}}),
        encoding="utf-8",
    )

    meta = br._source_meta({"src": str(tmp_path), "counts": {"openrouter": 10, "livebench": 5}})

    assert meta["OpenRouter"]["refresh_failed"] is True
    assert meta["OpenRouter"]["refresh_error"] == "or down"
    assert "refresh_failed" not in meta["LiveBench"]


def test_source_meta_is_clean_without_a_status_file(tmp_path):
    meta = br._source_meta({"src": str(tmp_path), "counts": {}})

    assert all("refresh_failed" not in entry for entry in meta.values())


def test_failed_refresh_reaches_the_shipped_artifact():
    tmp = tempfile.mkdtemp(prefix="refresh_")
    dest = os.path.join(tmp, "data")
    shutil.copytree(DATA_DIR, dest, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("model_registry.json", "axes_catalog.json", "processed.js", "manifest.json"):
        path = os.path.join(dest, name)
        if os.path.exists(path):
            os.remove(path)
    with open(os.path.join(dest, "sources", ps.PULL_STATUS_FILE), "w", encoding="utf-8") as f:
        json.dump({"checked_at": "2026-09-25T00:00:00Z", "ok": ["aa_public_catalog"], "failed": {"openrouter": "or down"}}, f)

    build_from_cache({"root": tmp})

    with open(os.path.join(dest, "processed.js"), encoding="utf-8") as f:
        raw = f.read().strip().removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    meta = json.loads(raw)["meta"]["sources_meta"]
    assert meta["OpenRouter"]["refresh_failed"] is True
    assert meta["OpenRouter"]["refresh_error"] == "or down"
    shutil.rmtree(tmp, ignore_errors=True)
