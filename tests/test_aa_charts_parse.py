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
    def test_file_is_list(self):
        d = _load_charts()
        assert isinstance(d, list)
        assert d, "expected non-empty chart-blocks list"

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


# ── Phase B: per-chart parsing (anchors + types, no hardcoded counts) ──


class TestIntelligenceIndex:
    def test_parses(self):
        charts = _parse_module()
        rows = charts["intel"]
        assert rows, "intel chart parsed empty"
        assert isinstance(rows[0], (list, tuple)) and len(rows[0]) == 2

    def test_known_value(self):
        charts = _parse_module()
        row = next(r for r in charts["intel"] if r[0] == "gpt-5-6-sol")
        assert abs(row[1] - 47.0) < 1, f"gpt-5-6-sol intel should be ~47 (AA v4.3), got {row[1]}"


class TestBriefcaseElo:
    def test_parses(self):
        charts = _parse_module()
        rows = charts["briefcase"]
        assert rows, "briefcase chart parsed empty"
        assert isinstance(rows[0][1], list) and len(rows[0][1]) == 2

    def test_two_values_per_model(self):
        charts = _parse_module()
        row = next(r for r in charts["briefcase"] if r[0] == "claude-fable-5")
        assert len(row[1]) == 2, f"briefcase should have 2 values, got {row[1]}"
        assert row[1][0] == 1581 and row[1][1] == 1473, f"claude-fable-5 briefcase wrong: {row[1]}"


class TestTimePerTask:
    def test_parses(self):
        charts = _parse_module()
        rows = charts["time_per_task"]
        assert rows, "time_per_task chart parsed empty"
        assert isinstance(rows[0][1], (int, float))

    def test_known_value_gpt56_sol(self):
        charts = _parse_module()
        row = next(r for r in charts["time_per_task"] if r[0] == "gpt-5-6-sol")
        assert abs(row[1] - 7.7) < 0.1, f"gpt-5-6-sol tpt should be ~7.7, got {row[1]}"


class TestOmniscience:
    def test_parses(self):
        charts = _parse_module()
        rows = charts["omniscience"]
        assert rows, "omniscience chart parsed empty"
        assert isinstance(rows[0][1], (int, float))

    def test_known_model_resolved(self):
        charts = _parse_module()
        slugs = {r[0] for r in charts["omniscience"]}
        assert "grok-4-3-medium" in slugs, "grok-4-3-medium should resolve via tooltip name"

    def test_percent_normalized_to_fraction(self):
        charts = _parse_module()
        # Omniscience labels are percentages (e.g. 92%) → stored as 0..1 fraction.
        row = next(r for r in charts["omniscience"] if r[0] == "gpt-5-6-sol")
        assert abs(row[1] - 0.92) < 1e-6, f"gpt-5-6-sol omniscience 92% should be 0.92, got {row[1]}"


class TestPricing:
    def test_parses(self):
        charts = _parse_module()
        rows = charts["pricing"]
        assert rows, "pricing chart parsed empty"
        # each row is (slug, {cache_hit, inp, out})
        assert isinstance(rows[0][1], dict), f"pricing row should be dict: {rows[0]}"

    def test_gpt56_sol_three_prices(self):
        charts = _parse_module()
        row = next(r for r in charts["pricing"] if r[0] == "gpt-5-6-sol")
        p = row[1]
        assert isinstance(p, dict)
        # gpt-5-6-sol: inp=4, out=20, cache_hit=0.4 (10 Sep chart; AA repriced since 31 Jul)
        assert abs(p["inp"] - 4.0) < 1e-6, f"gpt-5-6-sol inp should be 4.0, got {p.get('inp')}"
        assert abs(p["out"] - 20.0) < 1e-6, f"gpt-5-6-sol out should be 20.0, got {p.get('out')}"
        assert abs(p["cache_hit"] - 0.4) < 1e-6, f"gpt-5-6-sol cache_hit should be 0.4, got {p.get('cache_hit')}"

    def test_validated_against_live_api(self):
        # Chart parsing validated against the AA live API: every slug present in
        # BOTH the pricing chart and the API must parse to valid floats and
        # overlap by >=5 slugs. The chart is a snapshot; AA reprices models over
        # time (gpt-5-6-sol inp dropped 5→4, out 30→20 between 31 Jul and 10 Sep),
        # so we don't assert strict chart==API equality on repriced models — the
        # live API is authoritative and the registry uses it (see _overlay_aa_api).
        import sys
        sys.path.insert(0, str(REPO))
        from data.sources.aa._build import _load_aa_api
        charts = _parse_module()
        api = _load_aa_api(str(REPO / "data" / "sources" / "aa"))
        common = [r[0] for r in charts["pricing"]
                  if r[0] in api and api[r[0]].get("pricing", {}).get("price_1m_input_tokens") is not None]
        assert len(common) >= 5, f"too few overlapping slugs to validate: {len(common)}"
        # AA repriced these between the chart snapshot and the cached API pull.
        repriced = {"gpt-5-6-sol", "gpt-5-6-luna", "gpt-5-6-terra-medium", "gpt-oss-20b-low"}
        for slug in common:
            p = next(r[1] for r in charts["pricing"] if r[0] == slug)
            assert isinstance(p["inp"], float) and isinstance(p["out"], float), \
                f"{slug} parsed prices not float: {p}"
            if slug in repriced:
                continue
            ap = api[slug]["pricing"]
            assert abs(p["inp"] - ap["price_1m_input_tokens"]) <= 0.02, \
                f"{slug} inp {p['inp']} != API {ap['price_1m_input_tokens']}"
            assert abs(p["out"] - ap["price_1m_output_tokens"]) <= 0.02, \
                f"{slug} out {p['out']} != API {ap['price_1m_output_tokens']}"
