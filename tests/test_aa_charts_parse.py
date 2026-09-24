import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
AA_SOURCE = REPO / "data" / "sources" / "aa"
CHARTS = AA_SOURCE / "aa_charts_export.json"
JSONLD = AA_SOURCE / "aa_jsonld_export.json"
sys.path.insert(0, str(REPO / "data"))
from sources.aa._parse_charts import parse_aa_charts


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _charts():
    return parse_aa_charts(str(CHARTS)).unwrap()


def _datasets():
    return {entry["name"]: entry["data"] for entry in _load(JSONLD)
            if entry.get("@type") == "Dataset"}


def _slug(entry):
    return (entry.get("detailsUrl") or "").removeprefix("/models/")


def _property_value(entry, field, name):
    return next((item.get("value") for item in entry.get(field, [])
                 if item.get("name") == name), None)


def _assert_chart_matches_dataset(charts, key, dataset_name, value_of, tolerance, minimum_overlap):
    chart_values = dict(charts[key])
    dataset_values = {_slug(entry): value_of(entry)
                      for entry in _datasets()[dataset_name]}
    common = {slug for slug in chart_values.keys() & dataset_values.keys()
              if dataset_values[slug] is not None}
    assert len(common) >= minimum_overlap
    for slug in common:
        assert abs(chart_values[slug] - dataset_values[slug]) <= tolerance, (
            f"{slug}: chart {chart_values[slug]} != JSON-LD {dataset_values[slug]}"
        )


def test_recognized_chart_contract():
    charts = _charts()
    expected = {
        "intel", "pricing", "cost_per_task", "time_per_task",
        "finance_accounting_index", "analyst_agent_pass_5",
        "briefcase_elo", "gdpval_elo", "omniscience_index", "output_speed",
    }
    assert expected <= charts.keys()
    assert not {"coding_index", "cost_to_run", "briefcase", "omniscience"} & charts.keys()


def test_chart_export_has_real_surfaces_for_ingested_charts():
    source = _load(CHARTS)
    required = {
        "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
        "Pricing: Cache Hit, Input, and Output",
        "Cost per Intelligence Index Task",
        "Time per Intelligence Index Task",
        "Artificial Analysis Finance & Accounting Index",
        "AA-AnalystAgent pass^5", "AA-Briefcase Elo",
        "GDPval-AA v2.1 Leaderboard", "AA-Omniscience Index", "Output Speed",
    }
    for entry in source:
        title = (entry.get("spans") or [""])[0]
        if title in required:
            assert "recharts-surface" in entry.get("svg", ""), title
    assert not any(entry.get("svg") and "recharts-surface" not in entry["svg"]
                   for entry in source)


@pytest.mark.parametrize(
    "key,dataset,value_of,tolerance,minimum_overlap",
    [
        ("intel", "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
         lambda row: row.get("intelligenceIndex"), 0.6, 20),
        ("finance_accounting_index", "Artificial Analysis Finance & Accounting Index",
         lambda row: row.get("score"), 0.6, 20),
        ("briefcase_elo", "AA-Briefcase Elo",
         lambda row: _property_value(row, "aaBriefcaseElo", "mid"), 0.6, 20),
        ("analyst_agent_pass_5", "AA-AnalystAgent pass^5",
         lambda row: row.get("analystAgent"), 0.001, 13),
        ("gdpval_elo", "GDPval-AA v2.1 Leaderboard",
         lambda row: _property_value(row, "gdpvalAaElo", "mid"), 0.6, 20),
        ("omniscience_index", "AA-Omniscience Index",
         lambda row: row.get("omniscienceIndex"), 0.6, 20),
        ("time_per_task", "Time per Intelligence Index Task",
         lambda row: row.get("timePerTask"), 0.051, 20),
        ("output_speed", "Output Speed",
         lambda row: row.get("outputSpeed"), 0.6, 20),
    ],
)
def test_chart_values_match_jsonld(key, dataset, value_of, tolerance, minimum_overlap):
    _assert_chart_matches_dataset(_charts(), key, dataset, value_of, tolerance, minimum_overlap)


def test_intelligence_jsonld_views_are_value_identical():
    datasets = _datasets()
    left = {_slug(row): row["intelligenceIndex"]
            for row in datasets["Artificial Analysis Intelligence Index"]}
    right = {_slug(row): row["intelligenceIndex"]
             for row in datasets["Artificial Analysis Intelligence Index by Open Weights / Proprietary"]}
    common = left.keys() & right.keys()
    assert len(common) == 20
    assert all(left[slug] == right[slug] for slug in common)


def test_omniscience_index_keeps_negative_values():
    values = dict(_charts()["omniscience_index"])
    assert values["gpt-oss-120b"] == -49
    assert values["mistral-medium-3-5"] == -37


def test_task_cost_chart_matches_sourced_task_totals():
    charts = _charts()
    cost_values = dict(charts["cost_per_task"])
    datasets = _datasets()

    direct = {_slug(row): row.get("costPerIntelligenceIndexTask")
              for row in datasets["Cost per Task"]}
    direct_overlap = cost_values.keys() & direct.keys()
    assert len(direct_overlap) == 10
    for slug in direct_overlap:
        assert abs(cost_values[slug] - direct[slug]) <= 0.015

    components = {
        _slug(row): sum(row.get(key) or 0 for key in
                        ("answer", "reasoning", "cacheWrite", "cacheHit", "input"))
        for row in datasets["Cost per Intelligence Index Task"]
    }
    component_overlap = cost_values.keys() & components.keys()
    assert len(component_overlap) == 20
    for slug in component_overlap:
        assert abs(cost_values[slug] - components[slug]) <= 0.015


def test_pricing_chart_matches_jsonld_snapshot():
    charts = dict(_charts()["pricing"])
    datasets = _datasets()
    rows = {}
    for entry in datasets["Pricing: Cache Hit, Input, and Output"]:
        rows[_slug(entry)] = {
            "inp": _property_value(entry, "pricing", "inputPrice"),
            "out": _property_value(entry, "pricing", "outputPrice"),
        }
    common = charts.keys() & rows.keys()
    assert len(common) == 20
    for slug in common:
        for field in ("inp", "out"):
            assert abs(charts[slug][field] - rows[slug][field]) <= 0.02
