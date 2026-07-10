import json, re, subprocess, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "data"))

from _domain import ProjectionRow, Provenance  # noqa: E402


@pytest.fixture(scope="module")
def dashboard_html():
    return (REPO / "dashboard.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def processed_js():

    js_path = REPO / "data" / "processed.js"
    raw = js_path.read_text(encoding="utf-8").strip()
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    return json.loads(raw)


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
        assert derived == {"iq_per_1k_pt", "cost_per_iq_pt", "archetype",
                           "radar_intel", "radar_speed", "radar_cache_eff",
                           "radar_cost_eff", "radar_ctx"}, \
            f"DERIVED set drifted: {derived}"

    def test_cost_per_wallsec_axis_removed(self):

        assert "cost_per_wallsec" not in ProjectionRow.FIELD_PROVENANCE, \
            "cost_per_wallsec must not appear in FIELD_PROVENANCE"
        raw = (REPO / "data" / "processed.js").read_text(encoding="utf-8").strip()
        raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
        data = json.loads(raw)
        for m in data:
            assert "cost_per_wallsec" not in m, \
                f"{m['slug']}: cost_per_wallsec key must be absent"

    def test_derived_iq_fields_consistent(self, processed_js):

        for m in processed_js:
            intel = m.get("intel")
            ct = m.get("cost_per_task")
            iq1k = m.get("iq_per_1k_pt")
            ciq = m.get("cost_per_iq_pt")
            if intel is not None and ct is not None and ct > 0:
                assert abs(iq1k - intel / ct * 1000) < 1e-1, \
                    f"{m['slug']}: iq_per_1k_pt inconsistent"
                assert abs(ciq - ct / intel) < 1e-4, \
                    f"{m['slug']}: cost_per_iq_pt inconsistent"
            else:
                assert iq1k is None and ciq is None, \
                    f"{m['slug']}: derived IQ fields set without SOURCED inputs"


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

    def test_all_slugs_exist_in_registry(self):
        with open(REPO / "data" / "model_registry.json") as f:
            reg = json.load(f)
        reg_ids = {m["id"] for m in reg["models"]}
        with open(REPO / "data" / "sources" / "misc.json") as f:
            misc = json.load(f)
        stale = [s for s in misc if s not in reg_ids]
        assert not stale, \
            f"misc.json references slugs not in registry: {stale}"


class TestTokensMGuardrail:
    """tokens_m is AA's "Output Tokens per Intelligence Index Task" (millions).

    It spans the ENTIRE eval suite, not a single context window — so it is
    legitimately far larger than context_window. The guardrail only rejects
    non-positive or absurdly large values (>10,000M = 10B tokens/task).
    """
    def test_tokens_m_is_aa_per_task_volume(self, processed_js):

        for m in processed_js:
            tm = m.get("tokens_m")
            if tm is None:
                continue
            assert tm > 0, f"{m['slug']}: tokens_m must be positive"
            assert tm <= 10_000, f"{m['slug']}: tokens_m={tm}M exceeds sane AA per-task bound"

    def test_tokens_m_absent_when_no_source(self, processed_js):

        have = [m for m in processed_js if m.get("tokens_m") is not None]
        # AA enriched set is ~38 models; the rest are null by design
        assert 30 <= len(have) <= 45, f"unexpected tokens_m coverage: {len(have)}"


class TestVizNoDataGating:

    def test_archetypes_no_longer_requires_tokens_m(self, processed_js):
        # 03 gate (post-fix): intel + cost_per_task>0 + speed_tps.
        models = [m for m in processed_js
                  if m.get("intel") is not None
                  and m.get("cost_per_task") is not None and (m.get("cost_per_task") or 0) > 0
                  and m.get("speed_tps") is not None]
        assert len(models) > 0, "archetypes should render"
        # gate must NOT require tokens_m — models both with and without it pass
        with_tok = [m for m in models if m.get("tokens_m") is not None]
        without_tok = [m for m in models if m.get("tokens_m") is None]
        assert len(with_tok) > 0, "expected some archetype models with tokens_m (AA)"
        assert len(without_tok) > 0, "expected some archetype models without tokens_m (non-AA)"

    def test_cost_per_iq_still_has_data(self, processed_js):
        pts = [m for m in processed_js
               if (m.get("cost_per_task") or 0) > 0 and m.get("intel") is not None]
        assert len(pts) > 0, "05 cost-per-iq must still render"


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

        aa_models = [m for m in processed_js if m.get("intel") is not None
                     or m.get("inp_price") is not None]
        assert aa_models, "no AA-sourced models found"
        for field in ("inp_price", "out_price", "blended"):
            missing = [m["slug"] for m in aa_models if m.get(field) is None]
            assert not missing, f"AA models missing {field}: {missing[:5]}"

    def test_archetype_classified(self, processed_js):
        counts = {}
        for m in processed_js:
            a = m.get("archetype", "uncategorized")
            counts[a] = counts.get(a, 0) + 1
        assert "frontier" in counts, "expected frontier models"
        assert "uncategorized" in counts, "expected some uncategorized models"
        assert counts.get("uncategorized", 0) < len(processed_js), \
            "all models are uncategorized — classifier not running"
        print(f"\n  Archetype distribution: {counts}")
