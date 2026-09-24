"""Black-box Result-contract tests for data/_pull_sources.py.

No real network/parquet. Stub urllib at the I/O boundary (urlretrieve / urlopen)
and assert the observable Result behaviour: a dead source -> Err, a stubbed source
-> Ok(summary), and run() returns Err only when every source fails.
"""
import sys, os, json
from unittest import mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
import _pull_sources as ps  # noqa: E402


def test_pull_livebench_err_on_fetch_fail(tmp_path):
    src = str(tmp_path)
    with mock.patch.object(ps.urllib.request, "urlretrieve", side_effect=OSError("down")):
        r = ps.pull_livebench(src)
    assert r.is_err()
    assert "livebench table" in r.error


def test_pull_livebench_ok_when_files_written(tmp_path):
    src = str(tmp_path)
    csv_path = os.path.join(src, "livebench_2026_01_08.csv")
    json_path = os.path.join(src, "livebench_categories_2026_01_08.json")
    with mock.patch.object(ps.urllib.request, "urlretrieve",
                           side_effect=lambda url, fn: (open(fn, "w").write("a,b\n1,2\n") or None) if fn == csv_path else (open(json_path, "w").write('{"x":1}') or None)):
        r = ps.pull_livebench(src)
    assert r.is_ok()
    s = r.unwrap()
    assert s["columns"] == 2
    assert s["categories"] == ["x"]


def test_pull_openrouter_err_on_fetch_fail(tmp_path):
    src = str(tmp_path)
    with mock.patch.object(ps.urllib.request, "urlopen", side_effect=OSError("offline")):
        r = ps.pull_openrouter(src)
    assert r.is_err()
    assert "openrouter fetch" in r.error


def test_pull_openrouter_ok_normalizes(tmp_path):
    src = str(tmp_path)
    payload = json.dumps({"data": [
        {"id": "openai/gpt-5", "name": "GPT-5", "pricing": {"prompt": 1, "completion": 2}, "context_length": 100},
        {"id": "anthropic/claude", "pricing": {"input_cache_read": 0.5}, "context_length": 200},
    ]}).encode()
    fake = mock.MagicMock()
    fake.read.return_value = payload
    with mock.patch.object(ps.urllib.request, "urlopen", return_value=fake):
        r = ps.pull_openrouter(src)
    assert r.is_ok()
    assert r.unwrap()["models"] == 2
    saved = json.load(open(os.path.join(src, "openrouter_models.json")))
    assert saved[0]["vendor"] == "openai"
    assert saved[0]["input_price"] == 1


def test_run_err_when_all_sources_fail(tmp_path):
    src = str(tmp_path)
    with mock.patch.object(ps, "pull_livebench", return_value=ps.err("lb down")), \
         mock.patch.object(ps, "pull_openllm", return_value=ps.err("ol down")), \
         mock.patch.object(ps, "pull_openrouter", return_value=ps.err("or down")), \
         mock.patch.object(ps, "pull_aa_public_model_catalog", return_value=ps.err("aa catalog down")), \
         mock.patch.object(ps, "pull_dirac", return_value=ps.err("dirac down")):
        r = ps.run({"root": str(tmp_path.parent)})
    assert r.is_err()
    assert "all sources failed" in r.error


def test_run_ok_records_failed_subset(tmp_path):
    src = str(tmp_path)
    with mock.patch.object(ps, "pull_livebench", return_value=ps.err("lb down")), \
         mock.patch.object(ps, "pull_openllm", return_value=ps.ok({"rows": 0})), \
         mock.patch.object(ps, "pull_openrouter", return_value=ps.ok({"models": 0})), \
         mock.patch.object(ps, "pull_aa_public_model_catalog", return_value=ps.ok({"models": 0})), \
         mock.patch.object(ps, "pull_dirac", return_value=ps.ok({"rows": 0})):
        r = ps.run({"root": str(tmp_path.parent)})
    assert r.is_ok()
    s = r.unwrap()
    assert "livebench" in s["failed_sources"]
    assert "openllm" in s["ok_sources"]
    assert "openrouter" in s["ok_sources"]
    assert "aa_public_catalog" in s["ok_sources"]
    assert "dirac" in s["ok_sources"]


def test_parse_aa_public_model_catalog_extracts_model_rows():
    payload = b'''0:{"models":[
      {"slug":"gpt-6-luna-max","creator":{"name":"OpenAI"},
       "release":{"slug":"gpt-6-luna","name":"GPT-6 Luna"},"releaseDate":"2026-09-22"}
    ]}'''

    result = ps.parse_aa_public_model_catalog(payload)

    assert result.is_ok()
    assert result.unwrap() == [{
        "slug": "gpt-6-luna-max",
        "creator": {"name": "OpenAI"},
        "release": {"slug": "gpt-6-luna", "name": "GPT-6 Luna"},
        "releaseDate": "2026-09-22",
    }]


def test_parse_aa_public_model_catalog_rejects_missing_models():
    result = ps.parse_aa_public_model_catalog(b"0:{\"page\":\"catalog unavailable\"}")

    assert result.is_err()


def test_pull_aa_public_model_catalog_writes_full_source_shape(tmp_path):
    payload = b'''0:{"models":[
      {"slug":"gpt-6-luna-max","creator":{"name":"OpenAI"},
       "release":{"slug":"gpt-6-luna","name":"GPT-6 Luna"},"releaseDate":"2026-09-22"}
    ]}'''
    response = mock.MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response

    with mock.patch.object(ps.urllib.request, "urlopen", return_value=response):
        result = ps.pull_aa_public_model_catalog(str(tmp_path))

    assert result.is_ok()
    assert result.unwrap()["models"] == 1
    snapshot = json.loads((tmp_path / "aa" / "aa_public_model_catalog.json").read_text(encoding="utf-8"))
    assert snapshot["models"][0]["creator"]["name"] == "OpenAI"
    assert snapshot["models"][0]["release"]["slug"] == "gpt-6-luna"
