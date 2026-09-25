import json, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data"))

from data._domain import ProjectionRow, Provenance  # noqa: E402
from data._canonical import dirac_name_to_canonical  # noqa: E402
from data.sources.aa._build import get_aa_models  # noqa: E402


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
        assert have, "expected AA-scoped models with cache_hit_rate_max"

    def test_cache_hit_rate_field_provenance_sourced(self):
        assert ProjectionRow.FIELD_PROVENANCE.get("cache_hit_rate_max") == Provenance.SOURCED

    def test_provider_rates_slugs_are_canonical_ids(self):
        rates = json.loads((REPO / "data" / "sources" / "dirac" / "provider_rates.json").read_text(encoding="utf-8"))
        entries = [e for rows in rates.values() for e in rows]
        assert entries, "provider_rates.json is empty"
        expected = {dirac_name_to_canonical(e["model_name"]).unwrap_or(None) for e in entries}
        assert None not in expected, "a dirac model_name does not resolve through DIRAC_NAME_MAP"
        assert {e["slug"] for e in entries} == expected, "provider_rates.json slugs must equal the canonical ids"

    def test_no_record_carries_only_dirac_rows(self):
        reg = _load_registry()
        shells = []
        for m in reg["models"]:
            if not m.get("meta", {}).get("dirac_cache_hit_rates"):
                continue
            aa_pricing = m.get("pricing", {}).get("aa", {}) or {}
            aa_bench = m.get("benchmarks", {}).get("aa", {}) or {}
            other_pricing = {s: v for s, v in m.get("pricing", {}).items() if s != "aa" and v}
            if not any(v is not None for v in aa_pricing.values()) \
                    and not any(v is not None for v in aa_bench.values()) \
                    and not other_pricing and not m.get("name"):
                shells.append(m["id"])
        assert not shells, f"dirac rows attached to nameless shell records: {shells}"

    def test_provider_rows_attach_only_to_real_models(self, processed_js):
        with_dirac = [m for m in processed_js if m.get("dirac_cache_hit_rates")]
        assert with_dirac
        unsourced = [m["slug"] for m in with_dirac
                     if not any(m.get(f) is not None for f in
                                ("intel", "cost_per_task", "inp_price", "out_price", "context_window",
                                 "aa_finance_accounting_index", "aa_analyst_agent_pass_5",
                                 "aa_briefcase_elo", "aa_gdpval_elo", "aa_omniscience_index",
                                 "aa_time_per_task", "livebench_average", "arena_code_elo",
                                 "arena_text_elo", "openllm_average", "openrouter_inp_price_per_m",
                                 "params_b"))]
        assert not unsourced, f"dirac rows on models with no other sourced data: {unsourced}"


class TestModelScope:
    def test_processed_models_match_primary_aa_exports(self, processed_js):
        expected = set(get_aa_models(REPO).unwrap())
        actual = {model["slug"] for model in processed_js}
        assert actual == expected

    def test_sourced_values_include_field_provenance(self, processed_js):
        for model in processed_js:
            provenance = model["provenance"]
            if model.get("intel") is not None:
                assert provenance["intel"] == "sourced"
            if model.get("reasoning_tax_pct") is not None:
                assert provenance["reasoning_tax_pct"] == "derived"
            for field in (
                "aa_finance_accounting_index", "aa_analyst_agent_pass_5",
                "aa_briefcase_elo", "aa_gdpval_elo", "aa_omniscience_index",
                "aa_time_per_task",
            ):
                if model.get(field) is not None:
                    assert provenance[field] == "sourced"


# ── (E) params_b plumbing ──


class TestParamsBPlumbing:
    def test_params_b_is_sourced_for_export_models(self):
        reg = _load_registry()
        expected_ids = set(get_aa_models(REPO).unwrap())
        assert {model["id"] for model in reg["models"]} == expected_ids

        sourced = [
            model for model in reg["models"]
            if model.get("meta", {}).get("params_b") is not None
        ]
        assert {model["id"] for model in sourced} <= expected_ids
        processed = {model["slug"]: model for model in _load_processed()}
        for model in sourced:
            assert processed[model["id"]]["params_b"] == model["meta"]["params_b"]


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


# ── (H) RegistryModel entity layer wired as typed serializer ──


class TestRegistryModelSerialization:
    def test_registry_roundtrips_through_entities(self):
        # The dead _domain._entities.RegistryModel is now the validating serializer
        # for model_registry.json. Every model must construct + round-trip cleanly.
        from data._domain._entities import RegistryModel
        reg = _load_registry()
        for m in reg["models"]:
            result = RegistryModel.from_flat(m)
            assert result.is_ok(), f"{m['id']}: {result.error if result.is_err() else ''}"
            out = result.unwrap().to_dict()
            assert out["id"] == m["id"], f"id lost for {m['id']}"
            assert out.get("family") == m.get("family")
            # meta fields preserved
            src_meta = m.get("meta", {})
            out_meta = out.get("meta", {})
            for k in ("release_date", "params_b", "context_window", "dirac_cache_hit_rates"):
                assert out_meta.get(k) == src_meta.get(k), f"{m['id']}: meta.{k} mismatch"
            # pricing/benchmarks dicts preserved (to_dict omits empty sections)
            assert (out.get("pricing") or {}) == (m.get("pricing") or {})
            assert (out.get("benchmarks") or {}) == (m.get("benchmarks") or {})


# ── (I) Live AA benchmarks promoted to real axes ──


class TestAaExportIndexes:
    OUTPUT_FIELDS = {
        "aa.intel": "intel",
        "aa.finance_accounting_index": "aa_finance_accounting_index",
        "aa.analyst_agent_pass_5": "aa_analyst_agent_pass_5",
        "aa.briefcase_elo": "aa_briefcase_elo",
        "aa.gdpval_elo": "aa_gdpval_elo",
        "aa.omniscience_index": "aa_omniscience_index",
        "aa.time_per_task": "aa_time_per_task",
    }
    NEW_AXES = list(OUTPUT_FIELDS)
    REMOVED_AXES = {
        "aa.aa_coding_index", "aa.aa_math_index", "aa.gpqa", "aa.mmlu_pro",
        "aa.hle", "aa.aime", "aa.aime_25", "aa.math_500", "aa.livecodebench",
        "aa.ifbench", "aa.lcr", "aa.scicode", "aa.tau2", "aa.tau_banking",
        "aa.terminalbench_hard", "aa.terminalbench_v2_1",
        "aa.omniscience_hallucination_rate",
        "aa.briefcase_analytical_quality_elo",
        "aa.briefcase_presentation_elo",
    }

    def test_axes_in_catalog(self):
        cat = json.loads((REPO / "data" / "axes_catalog.json").read_text(encoding="utf-8"))
        axis_ids = {axis["id"] for axis in cat["axes"]}
        assert set(self.NEW_AXES) <= axis_ids
        assert not self.REMOVED_AXES & axis_ids

    def test_export_metrics_populated_in_output(self, processed_js):
        for axis, field in self.OUTPUT_FIELDS.items():
            assert any(model.get(field) is not None for model in processed_js), axis


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
        assert have, "context_window should be available for matched export models"


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
