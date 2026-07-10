import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CHARTS = REPO / "data" / "sources" / "aa" / "aa_charts_export.json"


def _load_charts():
    with open(CHARTS) as f:
        return json.load(f)


def _parse_module():
    import sys
    sys.path.insert(0, str(REPO / "data"))
    from sources.aa._parse_charts import parse_aa_charts, CHART_MAP
    return parse_aa_charts(str(CHARTS)), CHART_MAP


# ── Phase A: core extraction ──


class TestChartStructure:
    def test_file_is_list_of_16(self):
        d = _load_charts()
        assert isinstance(d, list)
        assert len(d) == 16, f"expected 16 charts, got {len(d)}"

    def test_each_entry_has_svg_and_spans(self):
        d = _load_charts()
        for i, e in enumerate(d):
            assert "svg" in e and "spans" in e, f"entry {i} missing keys"
            assert isinstance(e["spans"], list) and len(e["spans"]) >= 1, \
                f"entry {i} spans malformed"


# ── Phase B: per-chart parsing (rigid, one per chart) ──


class TestCodingIndex:
    def test_parses_58_models(self):
        charts, _ = _parse_module()
        rows = charts["coding_index"]
        assert len(rows) == 58, f"coding: expected 58, got {len(rows)}"

    def test_known_value_gpt56_sol_xhigh(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["coding_index"] if r[0] == "gpt-5-6-sol-xhigh")
        assert abs(row[1] - 78.3) < 1e-6, f"gpt-5-6-sol-xhigh coding should be 78.3, got {row[1]}"


class TestIntelligenceIndex:
    def test_parses_106_models(self):
        charts, _ = _parse_module()
        rows = charts["intel"]
        assert len(rows) == 106, f"intel: expected 106, got {len(rows)}"

    def test_known_value(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["intel"] if r[0] == "gpt-5-6-sol")
        assert row[1] > 50, f"gpt-5-6-sol intel should be ~58.9, got {row[1]}"


class TestBriefcaseElo:
    def test_parses_35_models(self):
        charts, _ = _parse_module()
        rows = charts["briefcase"]
        assert len(rows) == 35, f"briefcase: expected 35, got {len(rows)}"

    def test_two_values_per_model(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["briefcase"] if r[0] == "claude-fable-5")
        assert len(row[1]) == 2, f"briefcase should have 2 values, got {row[1]}"
        assert row[1][0] == 1764 and row[1][1] == 1592, f"claude-fable-5 briefcase wrong: {row[1]}"


class TestTimePerTask:
    def test_parses_53_models(self):
        charts, _ = _parse_module()
        rows = charts["time_per_task"]
        assert len(rows) == 53, f"time_per_task: expected 53, got {len(rows)}"

    def test_known_value_gpt56_luna_medium(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["time_per_task"] if r[0] == "gpt-5-6-luna-medium")
        # SVG labels are rounded to 1 decimal (0.3); precise value (0.2963) lives in JSON-LD.
        assert abs(row[1] - 0.3) < 1e-6, f"gpt-5-6-luna-medium tpt label should be ~0.3, got {row[1]}"


class TestOmniscience:
    def test_parses_104_models(self):
        charts, _ = _parse_module()
        rows = charts["omniscience"]
        assert len(rows) == 104, f"omniscience: expected 104, got {len(rows)}"

    def test_known_model_resolved(self):
        charts, _ = _parse_module()
        slugs = {r[0] for r in charts["omniscience"]}
        assert "grok-4-3-medium" in slugs, "grok-4-3-medium should resolve via tooltip name"

    def test_percent_normalized_to_fraction(self):
        charts, _ = _parse_module()
        # Omniscience labels are percentages (e.g. 89%) → stored as 0..1 fraction.
        row = next(r for r in charts["omniscience"] if r[0] == "gpt-5-6-sol")
        assert abs(row[1] - 0.89) < 1e-6, f"gpt-5-6-sol omniscience 89% should be 0.89, got {row[1]}"


class TestCostToRun:
    def test_parses_models(self):
        charts, _ = _parse_module()
        rows = charts["cost_to_run"]
        assert len(rows) >= 40, f"cost_to_run: expected >=40, got {len(rows)}"

    def test_dollar_values_normalized(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["cost_to_run"] if r[0] == "gpt-oss-20b")
        # value(s) should be numeric floats, $ stripped
        vals = row[1] if isinstance(row[1], list) else [row[1]]
        assert all(isinstance(v, float) for v in vals), f"cost_to_run values not float: {row[1]}"


class TestPricing:
    def test_parses_models(self):
        charts, _ = _parse_module()
        rows = charts["pricing"]
        assert len(rows) >= 80, f"pricing: expected >=80, got {len(rows)}"

    def test_dollar_values_normalized(self):
        charts, _ = _parse_module()
        row = next(r for r in charts["pricing"] if r[0] == "gpt-5-6-sol")
        vals = row[1] if isinstance(row[1], list) else [row[1]]
        assert all(isinstance(v, float) for v in vals), f"pricing values not float: {row[1]}"
