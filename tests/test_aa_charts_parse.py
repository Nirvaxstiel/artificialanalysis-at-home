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
    from sources.aa._parse_charts import parse_aa_charts
    return parse_aa_charts(str(CHARTS)).unwrap()


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

    def test_only_bar_charts_parse(self):
        # AA removed the standalone "Coding Index" and "Cost to Run" bar charts;
        # those metrics are now sourced from JSON-LD (see test_jsonld_aa_source).
        # The charts file should therefore NOT expose coding_index / cost_to_run.
        charts = _parse_module()
        assert "coding_index" not in charts
        assert "cost_to_run" not in charts


# ── Phase B: per-chart parsing (rigid, one per chart) ──


class TestIntelligenceIndex:
    def test_parses_107_models(self):
        charts = _parse_module()
        rows = charts["intel"]
        assert len(rows) == 107, f"intel: expected 107, got {len(rows)}"

    def test_known_value(self):
        charts = _parse_module()
        row = next(r for r in charts["intel"] if r[0] == "gpt-5-6-sol")
        assert row[1] > 50, f"gpt-5-6-sol intel should be ~59, got {row[1]}"


class TestBriefcaseElo:
    def test_parses_36_models(self):
        charts = _parse_module()
        rows = charts["briefcase"]
        assert len(rows) == 36, f"briefcase: expected 36, got {len(rows)}"

    def test_two_values_per_model(self):
        charts = _parse_module()
        row = next(r for r in charts["briefcase"] if r[0] == "claude-fable-5")
        assert len(row[1]) == 2, f"briefcase should have 2 values, got {row[1]}"
        assert row[1][0] == 1600 and row[1][1] == 1346, f"claude-fable-5 briefcase wrong: {row[1]}"


class TestTimePerTask:
    def test_parses_62_models(self):
        charts = _parse_module()
        rows = charts["time_per_task"]
        assert len(rows) == 62, f"time_per_task: expected 62, got {len(rows)}"

    def test_known_value_gpt56_luna_medium(self):
        charts = _parse_module()
        row = next(r for r in charts["time_per_task"] if r[0] == "gpt-5-6-luna-medium")
        # SVG labels are rounded to 1 decimal (0.3); precise value (0.2963) lives in JSON-LD.
        assert abs(row[1] - 0.3) < 1e-6, f"gpt-5-6-luna-medium tpt label should be ~0.3, got {row[1]}"


class TestOmniscience:
    def test_parses_105_models(self):
        charts = _parse_module()
        rows = charts["omniscience"]
        assert len(rows) == 105, f"omniscience: expected 105, got {len(rows)}"

    def test_known_model_resolved(self):
        charts = _parse_module()
        slugs = {r[0] for r in charts["omniscience"]}
        assert "grok-4-3-medium" in slugs, "grok-4-3-medium should resolve via tooltip name"

    def test_percent_normalized_to_fraction(self):
        charts = _parse_module()
        # Omniscience labels are percentages (e.g. 89%) → stored as 0..1 fraction.
        row = next(r for r in charts["omniscience"] if r[0] == "gpt-5-6-sol")
        assert abs(row[1] - 0.89) < 1e-6, f"gpt-5-6-sol omniscience 89% should be 0.89, got {row[1]}"


class TestPricing:
    def test_parses_models(self):
        charts = _parse_module()
        rows = charts["pricing"]
        assert len(rows) >= 80, f"pricing: expected >=80, got {len(rows)}"
        # each row is (slug, {cache_hit, inp, out})
        assert isinstance(rows[0][1], dict), f"pricing row should be dict: {rows[0]}"

    def test_gpt56_sol_three_prices(self):
        charts = _parse_module()
        row = next(r for r in charts["pricing"] if r[0] == "gpt-5-6-sol")
        p = row[1]
        assert isinstance(p, dict)
        # gpt-5-6-sol: inp=5, out=30, cache_hit=0.5 (validated vs AA live API shape)
        assert abs(p["inp"] - 5.0) < 1e-6, f"gpt-5-6-sol inp should be 5.0, got {p.get('inp')}"
        assert abs(p["out"] - 30.0) < 1e-6, f"gpt-5-6-sol out should be 30.0, got {p.get('out')}"
        assert abs(p["cache_hit"] - 0.5) < 1e-6, f"gpt-5-6-sol cache_hit should be 0.5, got {p.get('cache_hit')}"

    def test_validated_against_live_api(self):
        # Chart parsing validated against the AA live API: every slug present in
        # BOTH the pricing chart and the API must have matching inp/out prices.
        import sys
        sys.path.insert(0, str(REPO))
        from data.sources.aa._build import _load_aa_api
        charts = _parse_module()
        api = _load_aa_api(str(REPO / "data" / "sources" / "aa"))
        common = [r[0] for r in charts["pricing"]
                  if r[0] in api and api[r[0]].get("pricing", {}).get("price_1m_input_tokens") is not None]
        assert len(common) >= 5, f"too few overlapping slugs to validate: {len(common)}"
        for slug in common:
            p = next(r[1] for r in charts["pricing"] if r[0] == slug)
            ap = api[slug]["pricing"]
            # SVG labels are rounded (2 dp); allow <=0.02 rounding vs API.
            assert abs(p["inp"] - ap["price_1m_input_tokens"]) <= 0.02, \
                f"{slug} inp {p['inp']} != API {ap['price_1m_input_tokens']}"
            assert abs(p["out"] - ap["price_1m_output_tokens"]) <= 0.02, \
                f"{slug} out {p['out']} != API {ap['price_1m_output_tokens']}"
