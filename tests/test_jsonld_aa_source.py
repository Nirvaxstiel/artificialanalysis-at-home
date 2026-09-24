import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AA_SOURCE = REPO / "data" / "sources" / "aa"
JSONLD = AA_SOURCE / "aa_jsonld_export.json"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data"))
from data.sources.aa._build import get_aa_jsonld_models, get_aa_models


def _datasets():
    payload = json.loads(JSONLD.read_text(encoding="utf-8-sig"))
    return {entry["name"]: entry["data"] for entry in payload
            if entry.get("@type") == "Dataset"}


def _slug(entry):
    return (entry.get("detailsUrl") or "").removeprefix("/models/")


def _record_for_slug(records, slug):
    return next(record for record in records.values()
                if record.get("aliases", {}).get("aa") == slug)


def _property_value(entry, field, name):
    return next(item["value"] for item in entry.get(field, [])
                if item.get("name") == name)


def test_jsonld_dataset_contract():
    datasets = _datasets()
    required = {
        "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
        "AA-Omniscience Index", "AA-Briefcase Elo", "AA-AnalystAgent pass^5",
        "GDPval-AA v2.1 Leaderboard", "Artificial Analysis Finance & Accounting Index",
        "Cost per Intelligence Index Task", "Cost per Task",
        "Pricing: Cache Hit, Input, and Output", "Time per Intelligence Index Task",
    }
    removed = {
        "AA-Omniscience Hallucination Rate",
        "AA-Briefcase Analytical Quality & Presentation Elo",
        "Artificial Analysis Coding Index",
    }
    assert required <= datasets.keys()
    assert not removed & datasets.keys()
    assert all(rows for rows in datasets.values())


def test_intelligence_jsonld_views_are_identical():
    datasets = _datasets()
    views = [
        { _slug(row): row["intelligenceIndex"] for row in datasets[name] }
        for name in (
            "Artificial Analysis Intelligence Index",
            "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
        )
    ]
    assert len(views[0]) == 20
    assert views[0] == views[1]


def test_jsonld_loader_returns_new_metrics():
    records_result = get_aa_jsonld_models(str(AA_SOURCE))
    assert records_result.is_ok()
    records = records_result.unwrap()
    datasets = _datasets()
    mappings = (
        ("Artificial Analysis Finance & Accounting Index", "finance_accounting_index",
         lambda entry: entry["score"]),
        ("AA-AnalystAgent pass^5", "analyst_agent_pass_5",
         lambda entry: entry["analystAgent"]),
        ("AA-Briefcase Elo", "briefcase_elo",
         lambda entry: _property_value(entry, "aaBriefcaseElo", "mid")),
        ("GDPval-AA v2.1 Leaderboard", "gdpval_elo",
         lambda entry: _property_value(entry, "gdpvalAaElo", "mid")),
        ("AA-Omniscience Index", "omniscience_index",
         lambda entry: entry["omniscienceIndex"]),
    )
    for dataset_name, field, value_of in mappings:
        entry = datasets[dataset_name][0]
        record = _record_for_slug(records, _slug(entry))
        assert record["benchmarks"]["aa"][field] == value_of(entry)


def test_task_cost_components_are_per_task_values():
    records_result = get_aa_jsonld_models(str(AA_SOURCE))
    assert records_result.is_ok()
    records = records_result.unwrap()
    datasets = _datasets()
    entry = datasets["Cost per Intelligence Index Task"][0]
    record = _record_for_slug(records, _slug(entry))
    segments = record["pricing"]["aa"]["cost_segments"]
    expected = {
        "answer_usd": "answer",
        "reasoning_usd": "reasoning",
        "cache_write_usd": "cacheWrite",
        "cache_hit_usd": "cacheHit",
        "input_usd": "input",
    }
    for output_key, source_key in expected.items():
        assert segments[output_key] == entry[source_key]


def test_jsonld_parse_failure_is_a_result(tmp_path):
    (tmp_path / "aa_jsonld_export.json").write_text("{bad json", encoding="utf-8")
    result = get_aa_jsonld_models(str(tmp_path))
    assert result.is_err()


def test_current_cost_chart_wins_over_legacy_breakdown():
    result = get_aa_models(REPO)
    assert result.is_ok()
    records = result.unwrap()
    model = _record_for_slug(records, "mistral-medium-3-5")
    assert model["pricing"]["aa"]["cost_per_task"] == 0.44
