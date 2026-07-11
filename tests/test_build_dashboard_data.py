"""Black-box Result-contract tests for data/_build_dashboard_data.py build().

Asserts build() returns Ok(dict) on real sources and Err(reason) when the
processed.js write fails. Stub _write_js at the I/O boundary.
"""
import sys, os
from unittest import mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
import data._build_dashboard_data as dd  # noqa: E402
from data._result import ok, err  # noqa: E402

BASE = os.path.join(os.path.dirname(__file__), "..")


def test_build_ok_on_real_sources():
    r = dd.build({"root": BASE})
    assert r.is_ok()
    p = r.unwrap()
    assert "models" in p
    assert p["meta"]["model_count"] > 0


def test_build_err_on_write_failure():
    with mock.patch.object(dd, "_write_js", return_value=err("disk full")):
        r = dd.build({"root": BASE})
    assert r.is_err()
    assert r.error == "disk full"
