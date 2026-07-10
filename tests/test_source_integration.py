import json, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "data"))

from _domain import ProjectionRow, Provenance  # noqa: E402


def _load_processed():
    raw = (REPO / "data" / "processed.js").read_text(encoding="utf-8").strip()
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    data = json.loads(raw)
    if isinstance(data, dict) and "models" in data:
        data = data["models"]
    return data


def _load_registry():
    with open(REPO / "data" / "model_registry.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def processed_js():
    return _load_processed()


# ── (B) Dirac cache hit rate ──


class TestDiracCacheHitRate:
    def test_source_file_exists_and_shape(self):
        p = REPO / "data" / "sources" / "dirac" / "cache_hit_rates.json"
        assert p.exists(), "dirac cache_hit_rates.json missing"
        d = json.loads(p.read_text(encoding="utf-8"))
        assert "models" in d and isinstance(d["models"], list)
        assert len(d["models"]) > 0
        for rec in d["models"]:
            assert "model" in rec and "provider" in rec
            assert "cache_hit_rate" in rec
            assert 0 <= rec["cache_hit_rate"] <= 100

    def test_max_cache_hit_rate_axis_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        aids = {a["id"] for a in cat["axes"]}
        assert "dirac.cache_hit_rate_max" in aids, "dirac.cache_hit_rate_max axis missing from catalog"

    def test_models_have_cache_hit_rate(self, processed_js):
        have = [m for m in processed_js if m.get("cache_hit_rate_max") is not None]
        assert len(have) >= 10, f"expected >=10 models with cache_hit_rate_max, got {len(have)}"

    def test_cache_hit_rate_field_provenance_sourced(self):
        assert ProjectionRow.FIELD_PROVENANCE.get("cache_hit_rate_max") == Provenance.SOURCED


# ── (C) iq_per_dollar translation fix ──


class TestIqPerDollarTranslation:
    def test_iq_per_dollar_pt_populated_from_enriched(self, processed_js):
        have = [m for m in processed_js if m.get("iq_per_dollar_pt") is not None]
        assert len(have) >= 10, f"expected >=10 models with iq_per_dollar_pt, got {len(have)}"

    def test_iq_per_dollar_pt_units_iq_per_usd(self, processed_js):
        for m in processed_js:
            v = m.get("iq_per_dollar_pt")
            if v is None:
                continue
            assert v > 0, f"{m['slug']}: iq_per_dollar_pt must be positive"
            assert v < 100, f"{m['slug']}: iq_per_dollar_pt implausibly large ({v})"

    def test_iq_per_dollar_pt_provenance_sourced(self):
        assert ProjectionRow.FIELD_PROVENANCE.get("iq_per_dollar_pt") == Provenance.SOURCED


# ── (D) tokens_m direction ──


class TestTokensMDirection:
    def test_tokens_m_lower_is_better_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        ax = next(a for a in cat["axes"] if a["id"] == "aa.tokens_m")
        assert ax["higher_is_better"] is False, "tokens_m is verbosity; must be lower_is_better"
        assert "tokens" in ax["label"].lower()


# ── (E) params_b plumbing ──


class TestParamsBPlumbing:
    def test_params_b_reaches_output(self, processed_js):
        have = [m for m in processed_js if m.get("params_b") is not None]
        assert len(have) >= 10, f"expected params_b plumbed to output, got {len(have)}"

    def test_params_b_matches_registry(self):
        reg = _load_registry()
        proc = {m["slug"]: m for m in _load_processed()}
        checked = 0
        for m in reg["models"]:
            rb = m.get("meta", {}).get("params_b")
            if rb is None:
                continue
            pm = proc.get(m["id"], {}).get("params_b")
            if pm is None:
                continue
            assert abs(pm - rb) < 1e-6, f"{m['id']}: params_b registry {rb} != output {pm}"
            checked += 1
        assert checked >= 10, f"too few params_b cross-checks ({checked})"


# ── (F) processed.js meta block ──


class TestProcessedMetaBlock:
    def test_meta_block_present(self):
        raw = (REPO / "data" / "processed.js").read_text(encoding="utf-8").strip()
        raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
        data = json.loads(raw)
        assert isinstance(data, dict), "processed.js must be a wrapper dict, not a bare array"
        assert "meta" in data, "wrapper must carry meta block"
        assert data["meta"]["model_count"] == len(data["models"]), "model_count must equal len(models)"
        assert data["meta"]["version"] and data["meta"]["generated"]
        assert "sources" in data and "sources_meta" in data
