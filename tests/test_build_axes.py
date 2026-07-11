"""Black-box Result-contract tests for data/_build_axes.py run().

Asserts run() returns Ok(dict) on a readable registry and Err(reason) when the
registry load fails. Stub _load_json at the I/O boundary.
"""
import sys, os
from unittest import mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
import data._build_axes as ba  # noqa: E402
from data._result import ok, err  # noqa: E402

BASE = os.path.join(os.path.dirname(__file__), "..")


def test_run_ok_on_real_registry():
    r = ba.run({"root": BASE})
    assert r.is_ok()
    s = r.unwrap()
    assert "axis_count" in s
    assert s["axis_count"] > 0


def test_run_err_on_registry_missing():
    real = ba._load_json

    def fake(path):
        if path.endswith("model_registry.json"):
            return err("registry missing")
        return real(path)

    with mock.patch.object(ba, "_load_json", side_effect=fake):
        r = ba.run({"root": BASE})
    assert r.is_err()
    assert "registry" in r.error
