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
    """The static dashboard header must match the actual model/creator count."""

    def test_header_model_count(self, dashboard_html, processed_js):
        m = re.search(r"(\d+)\s+MODELS\s+·\s+(\d+)\s+CREATORS", dashboard_html)
        assert m, "Could not find header model/creator count"
        header_models = int(m.group(1))
        header_creators = int(m.group(2))
        assert header_models == len(processed_js), (
            f"Header says {header_models} models, actual {len(processed_js)}"
        )
        creators = {m["creator"] for m in processed_js if m.get("creator")}
        assert header_creators == len(creators), (
            f"Header says {header_creators} creators, actual {len(creators)}"
        )


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


# ── TEST 5: processed.js is valid JS (window assignment) ──


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
