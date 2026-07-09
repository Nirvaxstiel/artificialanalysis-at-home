import json, re, subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


# ── FIXTURES ──


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


# ── TEST 1: All creators have a color in the palette ──


class TestCreatorColors:
    """Every model creator in processed.js must have an entry in CREATOR_COLORS."""

    def test_all_creators_have_colors(self, processed_js, shared_js):
        creators = {m["creator"] for m in processed_js}
        # Extract CREATOR_COLORS keys from JS
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
        # Verify the header container has the dynamic-count element
        assert 'id="header-meta"' in dashboard_html, (
            "Missing #header-meta for dynamic model/creator count"
        )
        # Verify processed data has consistent counts
        assert len(processed_js) > 0, "No models in processed data"
        creators = {m["creator"] for m in processed_js if m.get("creator")}
        assert len(creators) > 0, "No creators in processed data"
        # Verify each model has required fields
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
            # Quick syntax check via Node.js
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
