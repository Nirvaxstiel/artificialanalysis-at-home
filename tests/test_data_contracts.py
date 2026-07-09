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
    """Load processed.js as a Python list."""
    js_path = REPO / "data" / "processed.js"
    raw = js_path.read_text(encoding="utf-8").strip()
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    return json.loads(raw)


@pytest.fixture(scope="module")
def shared_js():
    return (REPO / "viz" / "_shared.js").read_text(encoding="utf-8")


# ── Derived property guardrails ──


class TestDerivedProperties:
    """Guardrail for the whole class of DERIVED properties.

    A DERIVED field must never carry a value computed from a null, corrupt,
    or physically-impossible SOURCED input. This makes the domain model safe
    by construction: if a source feeds garbage, the DERIVED output is null,
    not wrong.
    """

    def test_all_fields_have_provenance(self):
        """Every ProjectionRow field must be tagged SOURCED or DERIVED."""
        annotated = set(ProjectionRow.FIELD_PROVENANCE)
        field_names = {f.name for f in ProjectionRow.__dataclass_fields__.values()}
        missing = field_names - annotated - {"meta", "FIELD_PROVENANCE"}
        assert not missing, f"Fields missing provenance tag: {missing}"

    def test_derived_fields_are_explicit(self):
        derived = {k for k, v in ProjectionRow.FIELD_PROVENANCE.items()
                    if v == Provenance.DERIVED}
        assert derived == {"iq_per_1k_pt", "cost_per_iq_pt", "cost_per_wallsec"}, \
            f"DERIVED set drifted: {derived}"

    def test_no_derived_value_from_corrupt_input(self, processed_js):
        """No DERIVED field may hold a value that implies a corrupt input.

        cost_per_wallsec = cost_per_task * speed_tps / (tokens_m * 1e6).
        Since tokens_m is nulled when impossible, any non-null cost_per_wallsec
        proves the derivation chain was fed valid inputs.
        """
        for m in processed_js:
            cws = m.get("cost_per_wallsec")
            if cws is None:
                continue
            ct = m.get("cost_per_task")
            sp = m.get("speed_tps")
            tm = m.get("tokens_m")
            ctx = m.get("context_window")
            assert ct is not None and ct > 0, f"{m['slug']}: cost_per_wallsec set but cost_per_task missing"
            assert sp is not None and sp > 0, f"{m['slug']}: cost_per_wallsec set but speed_tps missing"
            assert tm is not None, f"{m['slug']}: cost_per_wallsec set but tokens_m null (corrupt derivation)"
            # tokens_m is AA's per-task volume (millions) — legitimately large,
            # NOT bounded by context_window. Skip the context check here.
            expected = ct * sp / (tm * 1e6)
            assert abs(expected - cws) < 1e-6, \
                f"{m['slug']}: cost_per_wallsec {cws} != derived {expected}"

    def test_derived_iq_fields_consistent(self, processed_js):
        """iq_per_1k_pt and cost_per_iq_pt must equal their derivation from
        SOURCED intel + cost_per_task (or be null when inputs lack)."""
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
    """Every model creator in processed.js must have an entry in CREATOR_COLORS."""

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
    """Every script tag in dashboard.html must point to an existing file."""

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
    """The dashboard header displays dynamic model/creator count from data."""

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
    """Every viz/*.js file must be valid JavaScript (no syntax errors)."""

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
    """misc.json entries must be valid records referencing real models."""

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
        """tokens_m values present must be positive AA per-task token volumes
        (millions), within a sane bound. Not compared to context_window."""
        for m in processed_js:
            tm = m.get("tokens_m")
            if tm is None:
                continue
            assert tm > 0, f"{m['slug']}: tokens_m must be positive"
            assert tm <= 10_000, f"{m['slug']}: tokens_m={tm}M exceeds sane AA per-task bound"

    def test_tokens_m_absent_when_no_source(self, processed_js):
        """tokens_m is sourced only from AA's enriched file (38 models).
        Models without an AA per-task volume must be null, not zero/garbage."""
        have = [m for m in processed_js if m.get("tokens_m") is not None]
        # AA enriched set is ~38 models; the rest are null by design
        assert 30 <= len(have) <= 45, f"unexpected tokens_m coverage: {len(have)}"


class TestVizNoDataGating:
    """Each viz must gate on fields that actually carry data.
    Archetypes radar must not require tokens_m (only AA models have it);
    04 speed-adjusted-cost now renders from valid AA tokens_m."""
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
    def test_speed_adjusted_cost_now_populated(self, processed_js):
        # 04 gate: cost_per_wallsec>0 + tokens_m + intel. tokens_m is AA's real
        # per-task volume (not corrupt), so cost_per_wallsec is legitimately derived.
        pts = [m for m in processed_js
               if (m.get("cost_per_wallsec") or 0) > 0
               and m.get("tokens_m") is not None
               and m.get("intel") is not None]
        assert len(pts) > 0, "04 should render — cost_per_wallsec derived from valid AA tokens_m"

    def test_cost_per_iq_still_has_data(self, processed_js):
        pts = [m for m in processed_js
               if (m.get("cost_per_task") or 0) > 0 and m.get("intel") is not None]
        assert len(pts) > 0, "05 cost-per-iq must still render"


class TestProcessedJS:
    """processed.js must parse as valid JavaScript (no syntax errors)."""

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

    def test_aa_pricing_fully_populated(self, processed_js):
        """AA-sourced pricing fields should be populated for AA models
        (live API fill at source-fetch stage)."""
        aa_models = [m for m in processed_js if m.get("intel") is not None
                     or m.get("inp_price") is not None]
        assert aa_models, "no AA-sourced models found"
        for field in ("inp_price", "out_price", "blended"):
            missing = [m["slug"] for m in aa_models if m.get(field) is None]
            assert not missing, f"AA models missing {field}: {missing[:5]}"
