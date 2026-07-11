"""Black-box Result-contract tests for data/sources/aa/_build.py.

Asserts the observable Result behaviour of _load_json and get_aa_models without
needing real AA source dumps. Stub _load_json at the I/O boundary.
"""
import sys, os, json
from unittest import mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from data.sources.aa import _build as aab  # noqa: E402
from data._result import ok, err  # noqa: E402


def test_load_json_ok(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"a": 1}')
    r = aab._load_json(str(p))
    assert r.is_ok()
    assert r.unwrap() == {"a": 1}


def test_load_json_err_missing():
    r = aab._load_json("/nonexistent/path/x.json")
    assert r.is_err()


def test_load_json_err_malformed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    r = aab._load_json(str(p))
    assert r.is_err()


def test_get_aa_models_err_when_required_missing():
    with mock.patch.object(aab, "_load_json", return_value=err("aa_models_scraped.json: missing")):
        r = aab.get_aa_models("/some/base")
    assert r.is_err()
    assert "aa_models_scraped" in r.error


def test_get_aa_models_ok_with_empty_sources():
    with mock.patch.object(aab, "_load_json", return_value=ok({})):
        with mock.patch.object(aab, "get_aa_charts_models", return_value={}), \
             mock.patch.object(aab, "get_aa_jsonld_models", return_value={}), \
             mock.patch.object(aab, "get_aa_live_models", return_value={}), \
             mock.patch.object(aab, "_load_aa_api", return_value={}):
            r = aab.get_aa_models("/some/base")
    assert r.is_ok()
    assert isinstance(r.unwrap(), dict)


def test_get_aa_models_ok_when_costbd_optional_missing():
    side = {"aa_models_scraped.json": ok({}), "aa_model_data.json": ok({}),
            "aa_cost_breakdown.json": err("missing")}
    with mock.patch.object(aab, "_load_json", side_effect=lambda p: side.get(os.path.basename(p), ok({}))):
        with mock.patch.object(aab, "get_aa_charts_models", return_value={}), \
             mock.patch.object(aab, "get_aa_jsonld_models", return_value={}), \
             mock.patch.object(aab, "get_aa_live_models", return_value={}), \
             mock.patch.object(aab, "_load_aa_api", return_value={}):
            r = aab.get_aa_models("/some/base")
    assert r.is_ok()
