"""Black-box Result-contract tests for data/_build_registry.py run().

Asserts run() returns Ok(dict) on a readable source set and Err(reason) when a
required source load fails. No full pipeline; stub _load_json at the I/O boundary.
"""
import sys, os
from unittest import mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
import data._build_registry as br  # noqa: E402
from data._result import ok, err  # noqa: E402

BASE = os.path.join(os.path.dirname(__file__), "..")


def test_run_ok_on_real_sources():
    r = br.run({"root": BASE})
    assert r.is_ok()
    s = r.unwrap()
    assert "model_count" in s
    assert s["model_count"] > 0


def test_run_err_on_required_load_failure():
    real = br._load_csv

    def fake_load(path):
        if path.endswith("livebench_2026_01_08.csv"):
            return err("csv missing")
        return real(path)

    with mock.patch.object(br, "_load_csv", side_effect=fake_load):
        r = br.run({"root": BASE})
    assert r.is_err()
    assert "csv" in r.error


def test_run_err_on_aa_build_failure():
    with mock.patch.object(br, "get_aa_models", return_value=err("aa_models_scraped.json: missing")):
        r = br.run({"root": BASE})
    assert r.is_err()
    assert "aa build" in r.error
