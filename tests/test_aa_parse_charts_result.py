"""Black-box Result-contract tests for data/sources/aa/_parse_charts.py.

Asserts parse_aa_charts returns Ok(dict) on a readable source and Err(reason)
when the file is missing/malformed. Reuses the real aa_charts_export.json so the
happy path is exercised against actual data; the failure path stubs _load_json.
"""
import sys, os, json
from unittest import mock
import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO, "data"))
from sources.aa._parse_charts import parse_aa_charts, CHART_TITLE_MAP  # noqa: E402
from _result import ok, err  # noqa: E402

CHARTS = os.path.join(REPO, "data", "sources", "aa", "aa_charts_export.json")


def test_ok_on_real_export():
    r = parse_aa_charts(str(CHARTS))
    assert r.is_ok()
    d = r.unwrap()
    assert isinstance(d, dict)
    # AA removed the standalone Coding Index / Cost to Run bar charts; those
    # metrics are now sourced from JSON-LD. Charts file should NOT expose them.
    assert "coding_index" not in d
    assert "cost_to_run" not in d
    assert "intel" in d


def test_err_on_missing_file():
    r = parse_aa_charts("/no/such/aa_charts_export.json")
    assert r.is_err()


def test_err_on_malformed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    r = parse_aa_charts(str(bad))
    assert r.is_err()


def test_err_propagates_from_load_json():
    import sources.aa._parse_charts as mod
    with mock.patch.object(mod, "_load_json", return_value=err("boom")):
        r = parse_aa_charts(str(CHARTS))
    assert r.is_err()
    assert r.error == "boom"
