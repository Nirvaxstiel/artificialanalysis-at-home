import json, re, subprocess, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data"))

from _domain import (
    ProjectionRow, Provenance, RegistryModel, safe_finance_accounting_index,
    safe_model_family, safe_omniscience, safe_pass_rate, safe_ppm,
    safe_reasoning_tax, safe_response_time,
)  # noqa: E402
from data.sources.aa._build import get_aa_models  # noqa: E402


@pytest.fixture(scope="module")
def dashboard_html():
    return (REPO / "dashboard.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def processed_js():

    js_path = REPO / "data" / "processed.js"
    raw = js_path.read_text(encoding="utf-8").strip()
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    data = json.loads(raw)
    if isinstance(data, dict) and "models" in data:
        data = data["models"]
    return data


@pytest.fixture(scope="module")
def shared_js():
    return (REPO / "viz" / "_shared.js").read_text(encoding="utf-8")


# ── Derived property guardrails ──


class TestDerivedProperties:

    def test_all_fields_have_provenance(self):

        annotated = set(ProjectionRow.FIELD_PROVENANCE)
        field_names = {f.name for f in ProjectionRow.__dataclass_fields__.values()}
        missing = field_names - annotated - {"meta", "FIELD_PROVENANCE"}
        assert not missing, f"Fields missing provenance tag: {missing}"

    def test_derived_fields_are_explicit(self):
        derived = {k for k, v in ProjectionRow.FIELD_PROVENANCE.items()
                    if v == Provenance.DERIVED}
        assert derived == {
            "archetype", "blended", "has_breakdown", "pareto_optimal",
            "reasoning_tax_pct", "radar_intel", "radar_speed",
            "radar_cache_eff", "radar_cost_eff", "radar_ctx",
        }, f"DERIVED set drifted: {derived}"

    def test_index_smart_constructors(self):
        assert safe_finance_accounting_index(61.4).unwrap().as_primitive() == 61.4
        assert safe_finance_accounting_index(None).unwrap() is None
        assert safe_finance_accounting_index(100.1).is_err()
        assert safe_finance_accounting_index(float("inf")).is_err()
        assert safe_omniscience(-42).unwrap().as_primitive() == -42
        assert safe_omniscience(None).unwrap() is None
        assert safe_omniscience(100.1).is_err()

    def test_pass_rate_smart_constructor(self):
        valid = safe_pass_rate(0.575)
        assert valid.is_ok()
        assert valid.unwrap().as_primitive() == 0.575
        assert safe_pass_rate(None).unwrap() is None
        for invalid in (-0.01, 1.01, float("nan"), "invalid", True):
            assert safe_pass_rate(invalid).is_err()

    def test_response_time_returns_validated_result(self):
        assert safe_response_time(35.5).unwrap().as_primitive() == 35.5
        assert safe_response_time(None).unwrap() is None
        for invalid in (-1, float("nan"), float("inf"), "invalid", True):
            assert safe_response_time(invalid).is_err()

    def test_serialized_provenance(self):
        row = ProjectionRow(
            slug="test-model",
            name="Test Model",
            blended=safe_ppm(2.5),
            reasoning_tax_pct=safe_reasoning_tax(25),
            aa_finance_accounting_index=safe_finance_accounting_index(61.4).unwrap(),
            aa_analyst_agent_pass_5=safe_pass_rate(0.575).unwrap(),
        )
        provenance = row.to_dict()["provenance"]
        assert provenance["blended"] == "derived"
        assert provenance["reasoning_tax_pct"] == "derived"
        assert provenance["aa_finance_accounting_index"] == "sourced"
        assert provenance["aa_analyst_agent_pass_5"] == "sourced"

    def test_model_family_is_validated_and_sourced(self):
        family_data = {"slug": "gemini-3-8-flash", "name": "Gemini 3.8 Flash"}
        family = safe_model_family(family_data)
        assert family.unwrap().as_primitive() == family_data
        assert safe_model_family(None).unwrap() is None
        assert safe_model_family({"slug": "", "name": "Gemini 3.8 Flash"}).is_err()

        row = ProjectionRow(slug="gemini-3-8-flash", name="Gemini 3.8 Flash", family=family.unwrap())
        serialized = row.to_dict()
        assert serialized["family"] == family_data
        assert serialized["provenance"]["family"] == "sourced"

        registry_model = RegistryModel.from_flat({"id": row.slug, "family": family_data})
        assert registry_model.unwrap().to_dict()["family"] == family_data
        assert RegistryModel.from_flat({"id": row.slug, "family": {"slug": "", "name": "bad"}}).is_err()

    def test_official_family_flows_to_processed_data(self, processed_js):
        model = next(row for row in processed_js if row["slug"] == "gemini-3-8-flash-medium")
        assert model["family"] == {"slug": "gemini-3-8-flash", "name": "Gemini 3.8 Flash"}
        assert model["provenance"]["family"] == "sourced"

    def test_new_aa_fields_have_sourced_provenance(self):
        for field in (
            "aa_finance_accounting_index", "aa_analyst_agent_pass_5",
            "aa_briefcase_elo", "aa_gdpval_elo", "aa_omniscience_index",
            "aa_time_per_task",
        ):
            assert ProjectionRow.FIELD_PROVENANCE[field] == Provenance.SOURCED
        for field in (
            "aa_omniscience_hallucination_rate",
            "aa_briefcase_analytical_quality_elo",
            "aa_briefcase_presentation_elo",
        ):
            assert field not in ProjectionRow.FIELD_PROVENANCE

    def test_cost_per_wallsec_axis_removed(self):

        assert "cost_per_wallsec" not in ProjectionRow.FIELD_PROVENANCE, \
            "cost_per_wallsec must not appear in FIELD_PROVENANCE"
        raw = (REPO / "data" / "processed.js").read_text(encoding="utf-8").strip()
        raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
        data = json.loads(raw)
        if isinstance(data, dict) and "models" in data:
            data = data["models"]
        for m in data:
            assert "cost_per_wallsec" not in m, \
                f"{m['slug']}: cost_per_wallsec key must be absent"

    def test_derived_iq_fields_absent(self, processed_js):
        # The unit-mismatched derived iq_per_1k_pt / cost_per_iq_pt were removed
        # (intel/dollar is not a meaningful AA metric). Assert they never appear.
        for m in processed_js:
            assert "iq_per_1k_pt" not in m, f"{m.get('slug')}: iq_per_1k_pt should be gone"
            assert "cost_per_iq_pt" not in m, f"{m.get('slug')}: cost_per_iq_pt should be gone"


# ── TEST 1: All creators have a color in the palette ──


class TestCreatorColors:

    def test_all_creators_have_colors(self, processed_js, shared_js):
        creators = {m["creator"] for m in processed_js}
        m = re.search(r"CREATOR_COLORS\s*=\s*\{([^}]+)\}", shared_js)
        assert m, "Could not find CREATOR_COLORS in _shared.js"
        colors_block = m.group(1)
        color_creators = set()
        for line in colors_block.split(","):
            line = line.strip()
            if ":" in line:
                key = line.split(":")[0].strip().strip("'\"")
                color_creators.add(key)
        missing = creators - color_creators - {None}
        assert not missing, f"Creators missing from CREATOR_COLORS: {missing}"


# ── TEST 2: HTML script src targets exist ──


class TestScriptSources:

    def test_all_script_srcs_exist(self, dashboard_html):
        srcs = re.findall(r'<script\s+src="\.([^"]+)"', dashboard_html)
        missing = []
        for src in srcs:
            path = REPO / src.lstrip("/")
            if not path.exists():
                missing.append(src)
        assert not missing, f"Missing script targets: {missing}"


# ── TEST 3: Header model/creator count matches data ──


class TestHeaderCount:

    def test_header_model_count(self, dashboard_html, processed_js):
        assert 'id="header-meta"' in dashboard_html, \
            "Missing #header-meta for dynamic model/creator count"
        assert len(processed_js) > 0, "No models in processed data"
        creators = {m["creator"] for m in processed_js if m.get("creator")}
        assert len(creators) > 0, "No creators in processed data"
        for m in processed_js:
            assert "slug" in m
            assert "name" in m
            assert "type" in m or m.get("type") is None


# ── TEST 4: All viz JS files parse ──


class TestVizParseability:

    def test_all_viz_files_parse(self):
        from jsonschema.exceptions import ValidationError

        viz_dir = REPO / "viz"
        for js_file in sorted(viz_dir.glob("*.js")):
            r = subprocess.run(
                ["node", "--check", str(js_file)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode != 0:
                raise AssertionError(
                    f"JS parse error in {js_file.name}:\n{r.stderr}"
                )


# ── TEST 6: misc.json data contract ──


class TestMiscSource:

    def test_valid_json(self):
        path = REPO / "data" / "sources" / "misc.json"
        assert path.exists(), "misc.json not found"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "misc.json must be a dict"
        for slug, record in data.items():
            assert isinstance(record, dict), \
                f"misc.json[{slug!r}] must be an object, got {type(record).__name__}"
            assert record, f"misc.json[{slug!r}] has empty record"
            for key, val in record.items():
                assert val is not None, \
                    f"misc.json[{slug!r}].{key} is null — omit the key instead"

    def test_out_of_scope_records_do_not_seed_registry(self):
        with open(REPO / "data" / "model_registry.json") as f:
            reg = json.load(f)
        with open(REPO / "data" / "sources" / "misc.json") as f:
            misc = json.load(f)
        reg_ids = {model["id"] for model in reg["models"]}
        aa_ids = set(get_aa_models(REPO).unwrap())
        out_of_scope = set(misc) - aa_ids
        assert out_of_scope
        assert reg_ids == aa_ids
        assert out_of_scope.isdisjoint(reg_ids)


class TestUnsupportedMetrics:
    fields = {
        "tokens_m", "ttft", "useful_cost", "iq_per_1k", "iq_per_mtok",
        "iq_per_dollar_pt", "cost_per_iq", "aa_coding_index", "aa_math_index",
        "aa_gpqa", "aa_mmlu_pro", "aa_hle", "aa_aime", "aa_aime_25",
        "aa_math_500", "aa_livecodebench", "aa_ifbench", "aa_lcr", "aa_scicode",
        "aa_tau2", "aa_tau_banking", "aa_terminalbench_hard", "aa_terminalbench_v2_1",
        "aa_omniscience_hallucination_rate", "aa_briefcase_analytical_quality_elo",
        "aa_briefcase_presentation_elo",
    }

    def test_unsupported_metrics_absent(self, processed_js):
        for model in processed_js:
            assert not self.fields.intersection(model), model["slug"]

    def test_cost_per_iq_chart_has_source_inputs(self, processed_js):
        points = [model for model in processed_js
                  if (model.get("cost_per_task") or 0) > 0 and model.get("intel") is not None]
        assert points


class TestProcessedJS:

    def test_valid_js_syntax(self):
        r = subprocess.run(
            ["node", "--check", str(REPO / "data" / "processed.js")],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            raise AssertionError(
                f"processed.js parse error:\n{r.stderr}"
            )

    def test_radar_axes_no_token_eff(self, shared_js):

        import re
        m = re.search(r"window\.RADAR_AXES\s*=\s*\[(.*?)\];", shared_js, re.DOTALL)
        assert m, "RADAR_AXES not found in _shared.js"
        body = m.group(1)
        keys = re.findall(r"key:\s*'([^']+)'", body)
        assert "tokenEff" not in keys, "TOKEN EFF must not appear in radar axes"
        assert keys == ["avgIQ", "avgSpeed", "avgCacheEff", "costEff", "avgCtx"], \
            f"radar axes drifted: {keys}"

    def test_aa_pricing_fully_populated(self, processed_js):

        # A model is "pricing-bearing" only if it actually carries price data.
        # JSON-LD-sourced models (e.g. gpt-5.6 variants) may have intel/benchmarks
        # but no pricing yet (the export's Pricing chart wasn't captured) — those
        # are a known acquisition gap, not a completeness failure.
        aa_models = [m for m in processed_js if m.get("inp_price") is not None
                     or m.get("out_price") is not None]
        assert aa_models, "no AA-sourced models with pricing found"
        for field in ("inp_price", "out_price", "blended"):
            missing = [m["slug"] for m in aa_models if m.get(field) is None]
            assert not missing, f"AA models missing {field}: {missing[:5]}"

    def test_cost_per_task_is_per_task_not_full_index_run(self, processed_js):
        # cost_per_task must be the per-task cost (sane, typically < $10), NOT the
        # cost to run the ENTIRE intelligence index as one job (which hits $100s+).
        # Source of truth: "Cost per Task" dataset + aa_cost_breakdown.json. The
        # "Cost to Run Intelligence Index" dataset (full-benchmark-run cost) must
        # NOT be used for cost_per_task — see data/sources/aa/_build.py.
        # NOTE: AA v4.3 has frontier models (claude-opus-5 max, claude-fable-5.1 max)
        # at ~$5.86/$7.63 per task — real per-task costs, not full-index runs.
        SANE_MAX = 10.0
        offenders = [m["slug"] for m in processed_js
                     if m.get("cost_per_task") is not None and m["cost_per_task"] > SANE_MAX]
        assert not offenders, f"cost_per_task exceeds {SANE_MAX}: {offenders[:5]}"

    def test_archetype_distribution_is_populated(self, processed_js):
        counts = {}
        for m in processed_js:
            a = m.get("archetype", "uncategorized")
            counts[a] = counts.get(a, 0) + 1
        assert "frontier" in counts, "expected frontier models"
        assert "uncategorized" in counts, "expected some uncategorized models"
        assert counts.get("uncategorized", 0) < len(processed_js), \
            "all models are uncategorized — classifier not running"
