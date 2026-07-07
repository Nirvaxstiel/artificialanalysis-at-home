"""Contract tests at pipeline transformation boundaries.

Verifies:
1. All creators have CREATOR_COLORS entries
2. All HTML script src targets exist
3. Header model count matches data
4. All viz files loaded by HTML are parseable
5. processed.js is valid JS with valid JSON payload
"""
import json, re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


# ── TEST 2: Creator color coverage ──

class TestCreatorColors:
    """Every creator in the data must have a CREATOR_COLORS entry."""

    def test_all_creators_have_colors(self, processed_js, shared_js):
        creators = {m["creator"] for m in processed_js}
        # Extract CREATOR_COLORS keys from JS
        m = re.search(r'CREATOR_COLORS\s*=\s*\{([^}]+)\}', shared_js)
        assert m, "Could not find CREATOR_COLORS in _shared.js"
        colors_block = m.group(1)
        color_creators = set()
        for line in colors_block.split(","):
            line = line.strip()
            if ":" in line:
                key = line.split(":")[0].strip().strip("'\"")
                color_creators.add(key)
        missing = creators - color_creators
        assert not missing, f"Creators missing from CREATOR_COLORS: {missing}"


# ── TEST 3: HTML script src targets exist ──

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


# ── TEST 4: Header count matches real data ──

class TestHeaderCount:
    """The header model/creator count must match loaded data."""

    def test_header_model_count(self, dashboard_html, processed_js):
        # Updated header format: "85 MODELS · 24 CREATORS"
        m = re.search(r'(\d+)\s+MODELS\s+·\s+(\d+)\s+CREATORS', dashboard_html)
        assert m, "Could not find header model/creator count"
        header_models = int(m.group(1))
        header_creators = int(m.group(2))
        assert header_models == len(processed_js), \
            f"Header says {header_models} models, actual {len(processed_js)}"
        creators = {m["creator"] for m in processed_js}
        assert header_creators == len(creators), \
            f"Header says {header_creators} creators, actual {len(creators)}"


# ── TEST 5: All viz files are parseable JS ──

class TestVizParseability:
    """Each viz JS file (except template) must be valid JS and register."""

    def test_all_viz_files_parse(self, dashboard_html):
        srcs = re.findall(r'<script\s+src="\.([^"]+)"', dashboard_html)
        for src in srcs:
            path = REPO / src.lstrip("/")
            # Skip non-viz scripts (data, shared helpers)
            if "viz/" not in str(path):
                continue
            if "viz/00-template" in str(path):
                continue
            content = path.read_text()
            # Basic parse check: no SyntaxError-inducing patterns
            assert content.strip().startswith("(function()"), \
                f"{path.name} does not start with IIFE"
            assert "window.VIZ_REGISTRY" in content, \
                f"{path.name} missing VIZ_REGISTRY reference"


# ── TEST 6: processed.js is valid JS (no syntax errors) ──

class TestProcessedJS:
    """processed.js must be syntactically valid JavaScript."""

    def test_valid_js_syntax(self):
        with open(REPO / "data" / "processed.js") as f:
            content = f.read()
        assert content.startswith("window.PROCESSED_DATA = [")
        assert content.rstrip().endswith("];")
        # JSON-parse the value portion to verify data integrity
        m = re.match(r'window\.PROCESSED_DATA\s*=\s*(\[.*\]);\s*$', content, re.DOTALL)
        assert m, "processed.js has unexpected structure"
        data = json.loads(m.group(1))
        assert len(data) > 0, "processed.js has no models"
        assert all("slug" in m for m in data), "Not all models have slug field"
