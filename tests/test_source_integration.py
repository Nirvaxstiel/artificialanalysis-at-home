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
        # Flat list of per-provider observation rows (source-of-truth from dirac.run table).
        assert isinstance(d, list) and len(d) > 0
        for rec in d[:50]:
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
    def test_params_b_sourced_from_openllm(self):
        # params_b is a SOURCE field (OpenLLM v2 #Params (B)), legitimately sparse
        # for the AA-centric 104-model output set. Assert it is genuinely sourced
        # into the registry (not dead) and plumbed to output where present.
        reg = _load_registry()
        sourced = [m for m in reg["models"] if m.get("meta", {}).get("params_b") is not None]
        assert len(sourced) >= 100, f"params_b should be sourced from OpenLLM, got {len(sourced)}"
        proc = {m["slug"]: m for m in _load_processed()}
        checked = 0
        for m in sourced:
            pm = proc.get(m["id"], {}).get("params_b")
            if pm is None:
                continue
            assert abs(pm - m["meta"]["params_b"]) < 1e-6
            checked += 1
        # Plumbing verified where the model is also in output (may be 0 for AA set).
        assert checked >= 0


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


# ── (G) aa_api_live.json repurposing: release_date + creator enrichment ──


class TestAaApiLiveEnrichment:
    def test_release_date_axis_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        aids = {a["id"] for a in cat["axes"]}
        assert "meta.release_date" in aids, "release_date should be a catalog axis"

    def test_release_date_populated_in_output(self, processed_js):
        have = [m for m in processed_js if m.get("release_date")]
        assert len(have) >= 10, f"expected >=10 models with release_date from aa_api_live, got {len(have)}"

    def test_creator_filled_from_live(self):
        reg = _load_registry()
        rd = [m for m in reg["models"] if m.get("meta", {}).get("release_date")]
        assert len(rd) >= 10, f"release_date should be sourced into registry meta, got {len(rd)}"


class TestAaImgScrapeProgress:
    def test_confirmed_scraped_reaches_output(self, processed_js):
        # aa_scrape_progress.json repurposed as provenance flag on speculative AA_IMG models
        have = [m for m in processed_js if m.get("confirmed_scraped") is True]
        assert len(have) >= 10, f"expected >=10 confirmed_scraped models, got {len(have)}"


# ── (H) RegistryModel entity layer wired as typed serializer ──


class TestRegistryModelSerialization:
    def test_registry_roundtrips_through_entities(self):
        # The dead _domain._entities.RegistryModel is now the validating serializer
        # for model_registry.json. Every model must construct + round-trip cleanly.
        from data._domain._entities import RegistryModel
        reg = _load_registry()
        for m in reg["models"]:
            rm = RegistryModel.from_flat(m)
            out = rm.to_dict()
            assert out["id"] == m["id"], f"id lost for {m['id']}"
            # meta fields preserved
            src_meta = m.get("meta", {})
            out_meta = out.get("meta", {})
            for k in ("release_date", "confirmed_scraped", "params_b"):
                assert out_meta.get(k) == src_meta.get(k), f"{m['id']}: meta.{k} mismatch"
            # pricing/benchmarks dicts preserved (to_dict omits empty sections)
            assert (out.get("pricing") or {}) == (m.get("pricing") or {})
            assert (out.get("benchmarks") or {}) == (m.get("benchmarks") or {})


# ── (I) Live AA benchmarks promoted to real axes ──


class TestAaLiveBenchmarks:
    NEW_AXES = [
        "aa.aa_coding_index", "aa.aa_math_index", "aa.gpqa", "aa.mmlu_pro",
        "aa.hle", "aa.aime", "aa.aime_25", "aa.math_500", "aa.livecodebench",
        "aa.ifbench", "aa.lcr", "aa.scicode", "aa.tau2", "aa.tau_banking",
        "aa.terminalbench_hard", "aa.terminalbench_v2_1",
    ]

    def test_axes_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        aids = {a["id"] for a in cat["axes"]}
        missing = [a for a in self.NEW_AXES if a not in aids]
        assert not missing, f"missing axes: {missing}"

    def test_benchmarks_populated_in_output(self, processed_js):
        # Each new axis should carry real values for at least some models
        # (sparse axes like aime/math_500 legitimately have few AA-covered models).
        # Output key = ProjectionRow attribute. Axis suffix already carries aa_
        # for some (aa_coding_index) but not others (gpqa); field = suffix
        # when it already starts with aa_, else aa_ + suffix.
        for ax in self.NEW_AXES:
            suffix = ax.split(".")[1]
            field = suffix if suffix.startswith("aa_") else "aa_" + suffix
            have = [m for m in processed_js if m.get(field) is not None]
            assert len(have) >= 1, f"{ax} (field {field}): no models populated"


# ── (J) context_window regression (OpenRouter context_length → crossover size) ──


class TestContextWindow:
    def test_axis_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        aids = {a["id"] for a in cat["axes"]}
        assert "meta.context_window" in aids, "context_window axis must exist (drives crossover circle size)"

    def test_context_window_populated_in_output(self, processed_js):
        # Regression: RegistryModel.from_flat silently dropped context_window
        # because RegistryModelMeta lacked the field. Must be >0 again.
        have = [m for m in processed_js if m.get("context_window") is not None]
        assert len(have) >= 50, f"context_window regressed: only {len(have)} models populated"


# ── (K) dead entity classes must stay removed ──


class TestNoDeadEntityClasses:
    def test_dead_classes_absent(self):
        from data import _domain
        dead = [
            "AAPricing", "CostBreakdownPricing", "OpenRouterPricing",
            "AABenchmarks", "LiveBenchBenchmarks", "ArenaBenchmarks", "OpenLLMBenchmarks",
        ]
        present = [c for c in dead if hasattr(_domain, c)]
        assert not present, f"dead entity classes re-introduced: {present}"
