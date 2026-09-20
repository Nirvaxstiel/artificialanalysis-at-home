"""Black-box tests for the Dirac.run cache-hit table fetch/parse.

The live page is stubbed at the urllib boundary; parse_cache_table is exercised
on HTML shaped like dirac.run's #the-full-table (verified against the live page:
398 rows, 68 providers, identical to the committed snapshot).
"""
import json, os, sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from sources.dirac._fetch import parse_cache_table, pull_dirac  # noqa: E402

TABLE_HTML = """
<h2 id="the-full-table">The full table</h2>
<div class="post-table post-table--full">
  <table class="min-w-full border-collapse text-sm">
    <thead><tr>
      <th>Model Name</th><th>Provider</th><th>Eff. Input Price</th>
      <th>Eff. Output Price</th><th>Cache Hit Rate</th>
    </tr></thead>
    <tbody>
      <tr><td class="p-3">Zai_GLM_5</td><td class="p-3">SiliconFlow</td>
          <td class="p-3">$0.3100</td><td class="p-3">$2.5490</td>
          <td class="text-emerald-400">85.30%</td></tr>
      <tr><td class="p-3">Zai_GLM_5</td><td class="p-3">Baidu Qianfan</td>
          <td class="p-3">$0.3930</td><td class="p-3">$2.2390</td>
          <td class="text-emerald-400">54.70%</td></tr>
    </tbody>
  </table>
</div>
"""


class _Response:
    def __init__(self, body):
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_parse_cache_table_extracts_rows():
    r = parse_cache_table(TABLE_HTML)
    assert r.is_ok()
    rows = r.unwrap()
    assert rows == [
        {"model": "Zai_GLM_5", "provider": "SiliconFlow",
         "eff_input_price": 0.31, "eff_output_price": 2.549, "cache_hit_rate": 85.3},
        {"model": "Zai_GLM_5", "provider": "Baidu Qianfan",
         "eff_input_price": 0.393, "eff_output_price": 2.239, "cache_hit_rate": 54.7},
    ]


def test_parse_cache_table_err_without_anchor():
    r = parse_cache_table("<table><tr><td>x</td></tr></table>")
    assert r.is_err()
    assert "#the-full-table" in r.error


def test_pull_dirac_err_on_network_failure(tmp_path):
    with mock.patch.object(urllib_request(), "urlopen", side_effect=OSError("offline")):
        r = pull_dirac(str(tmp_path))
    assert r.is_err()
    assert "dirac fetch" in r.error


def test_pull_dirac_writes_raw_and_provider_files(tmp_path):
    with mock.patch.object(urllib_request(), "urlopen", return_value=_Response(TABLE_HTML)):
        r = pull_dirac(str(tmp_path))
    assert r.is_ok()
    assert r.unwrap() == {"rows": 2, "providers": 2}
    raw = json.loads((tmp_path / "dirac" / "cache_hit_rates.json").read_text())
    assert len(raw) == 2
    assert raw[0]["cache_hit_rate"] == 85.3
    assert (tmp_path / "dirac" / "provider_rates.json").exists()


def urllib_request():
    from sources.dirac import _fetch
    return _fetch.urllib.request
