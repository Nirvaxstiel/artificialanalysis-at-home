import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data"))
from data._canonical import resolve_from_slug
from data.sources.aa._build import _load_json, get_aa_models
from data.sources.aa._parse_charts import parse_aa_charts
AA_SOURCE = REPO / "data" / "sources" / "aa"
PRIMARY_DATASETS = {
    "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
    "Output Speed",
    "Speed",
    "Cost per Task",
    "Cost per Intelligence Index Task",
    "Pricing: Cache Hit, Input, and Output",
    "Artificial Analysis Finance & Accounting Index",
    "AA-Briefcase Elo",
    "AA-AnalystAgent pass^5",
    "AA-Omniscience Index",
    "GDPval-AA v2.1 Leaderboard",
    "Time per Intelligence Index Task",
}


def test_load_json_returns_result(tmp_path):
    source = tmp_path / "source.json"
    source.write_text('{"value": 1}', encoding="utf-8")
    assert _load_json(str(source)).unwrap() == {"value": 1}
    assert _load_json(str(tmp_path / "missing.json")).is_err()


def test_get_aa_models_requires_both_primary_exports(tmp_path):
    result = get_aa_models(tmp_path)
    assert result.is_err()
    assert "aa_charts_export.json" in result.error
    assert "aa_jsonld_export.json" in result.error


def test_get_aa_models_contains_only_models_in_current_exports():
    charts = parse_aa_charts(str(AA_SOURCE / "aa_charts_export.json")).unwrap()
    slugs = {slug for rows in charts.values() for slug, _ in rows}
    datasets = json.loads((AA_SOURCE / "aa_jsonld_export.json").read_text(encoding="utf-8-sig"))
    slugs.update(
        (entry.get("detailsUrl") or "").removeprefix("/models/")
        for dataset in datasets
        if dataset.get("name") in PRIMARY_DATASETS
        for entry in dataset.get("data", [])
    )
    expected = {resolve_from_slug(slug) for slug in slugs if resolve_from_slug(slug)}

    result = get_aa_models(REPO)
    assert result.is_ok(), result.error
    models = result.unwrap()
    assert set(models) == expected
    assert all(model["aliases"].get("aa") for model in models.values())
    assert all(model["name"] for model in models.values())


def test_aa_records_exclude_legacy_metric_fields():
    models = get_aa_models(REPO).unwrap()
    for model in models.values():
        assert set(model["benchmarks"]["aa"]) == {
            "intel", "finance_accounting_index", "analyst_agent_pass_5",
            "briefcase_elo", "gdpval_elo", "omniscience_index", "time_per_task",
        }
        assert set(model["pricing"]["aa"]) == {
            "inp_price", "out_price", "blended", "cache_hit_price", "cost_per_task",
            "speed_tps", "reasoning_tax_pct", "cost_segments",
        }


def test_public_catalog_fills_missing_creators_from_release_families():
    models = get_aa_models(REPO).unwrap()
    expected = {
        "claude-opus-5-5": "Anthropic",
        "deepseek-v4-1-flash": "DeepSeek",
        "gpt-6-luna": "OpenAI",
        "gpt-6-sol": "OpenAI",
        "grok-4-7": "SpaceXAI",
        "ling-3-0-flash-fin": "InclusionAI",
        "ling-3-0-flash-vl": "InclusionAI",
        "mimo-v2-6-pro": "Xiaomi",
        "step-5": "StepFun",
    }

    assert {model_id: models[model_id]["creator"] for model_id in expected} == expected
    assert all(models[model_id]["aliases"].get("aa_public_catalog") for model_id in expected)
    assert all(models[model_id]["meta"].get("release_date") for model_id in expected)
    assert models["k2-horizon-375b-a23b"]["creator"] == "MBZUAI Institute Of Foundation Models"


def test_public_catalog_assigns_models_to_official_release_families():
    models = get_aa_models(REPO).unwrap()

    assert models["gemini-3-8-flash-medium"]["family"] == {
        "slug": "gemini-3-8-flash",
        "name": "Gemini 3.8 Flash",
    }
    assert models["step-5"]["family"] == {
        "slug": "step-5-preview",
        "name": "Step 5 Preview",
    }
    assert models["qwen3-8-max"]["family"] == {
        "slug": "qwen3-8-max-0902",
        "name": "Qwen3.8 Max (0902)",
    }
    assert models["mistral-medium-3.5"]["family"] == {
        "slug": "mistral-medium-3-5",
        "name": "Mistral Medium 3.5",
    }


def test_get_aa_models_propagates_malformed_export(tmp_path):
    source = tmp_path / "data" / "sources" / "aa"
    source.mkdir(parents=True)
    (source / "aa_charts_export.json").write_text("{broken", encoding="utf-8")
    (source / "aa_jsonld_export.json").write_text("[]", encoding="utf-8")

    result = get_aa_models(tmp_path)
    assert result.is_err()
    assert "aa_charts_export.json" in result.error


def test_load_json_rejects_malformed_input(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text("{broken", encoding="utf-8")
    assert _load_json(str(source)).is_err()
