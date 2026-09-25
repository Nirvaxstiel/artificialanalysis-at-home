
import json, os, re
from pathlib import Path

from ..._canonical import resolve_from_slug, normalize_creator
from _result import ok, err


def _load_json(path: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return ok(json.load(f))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        return err(f"{os.path.basename(path)}: {e}")


def get_aa_metadata(aa_dir: str):
    path = os.path.join(aa_dir, "aa_api_live.json")
    if not os.path.exists(path):
        return ok({})
    loaded = _load_json(path)
    if loaded.is_err():
        return err(loaded.error)
    payload = loaded.unwrap()
    if not isinstance(payload, dict) or not isinstance(payload.get("data", []), list):
        return err("aa_api_live.json: expected a data list")
    if any(not isinstance(model, dict) for model in payload.get("data", [])):
        return err("aa_api_live.json: each model must be an object")
    out: dict[str, dict] = {}
    for m in payload.get("data", []):
        slug = m.get("slug")
        cid = resolve_from_slug(slug) if slug else None
        if not cid:
            continue
        creator = (m.get("model_creator") or {}).get("name")
        out[cid] = {
            "id": cid,
            "name": m.get("name"),
            "creator": normalize_creator(creator),
            "meta": {"release_date": m.get("release_date")},
            "aliases": {"aa": slug},
        }
    return ok(out)


def get_aa_public_model_catalog(aa_dir: str):
    path = os.path.join(aa_dir, "aa_public_model_catalog.json")
    if not os.path.exists(path):
        return ok({})
    loaded = _load_json(path)
    if loaded.is_err():
        return err(loaded.error)
    payload = loaded.unwrap()
    if not isinstance(payload, dict):
        return err("aa_public_model_catalog.json: expected an object")
    source_models = payload.get("models")
    if isinstance(source_models, dict):
        entries = []
        for slug, record in source_models.items():
            if not isinstance(record, dict):
                return err("aa_public_model_catalog.json: each model must be an object")
            family_result = _public_model_family(record.get("family"), slug)
            if family_result.is_err():
                return err(family_result.error)
            entries.append((slug, record.get("creator"), record.get("release_date"), family_result.unwrap()))
    elif isinstance(source_models, list):
        if any(not isinstance(model, dict) for model in source_models):
            return err("aa_public_model_catalog.json: each model must be an object")
        entries = []
        for model in source_models:
            release = model.get("release")
            model_slug = model.get("slug")
            family_result = _public_model_family(release, model_slug)
            if family_result.is_err():
                return err(family_result.error)
            release_slug = release.get("slug") if isinstance(release, dict) else None
            raw_creator = model.get("creator")
            creator = raw_creator.get("name") if isinstance(raw_creator, dict) else raw_creator
            if isinstance(model_slug, str):
                entries.append((model_slug, creator, model.get("releaseDate"), family_result.unwrap()))
            if isinstance(release_slug, str) and release_slug != model_slug:
                entries.append((release_slug, creator, None, None))
    else:
        return err("aa_public_model_catalog.json: expected a models list or map")

    out: dict[str, dict] = {}
    for slug, raw_creator, release_date, family in entries:
        if not isinstance(slug, str):
            continue
        if release_date is not None and not isinstance(release_date, str):
            return err(f"aa_public_model_catalog.json: invalid release date for {slug}")
        canonical_id = resolve_from_slug(slug)
        if not canonical_id:
            continue
        creator = normalize_creator(raw_creator)
        if creator is None and release_date is None and family is None:
            continue
        record = {
            "id": canonical_id,
            "creator": creator,
            "meta": {"release_date": release_date},
            "aliases": {"aa_public_catalog": slug},
        }
        if family is not None:
            record["family"] = family
        if canonical_id in out:
            existing = out[canonical_id]
            existing_creator = existing.get("creator")
            existing_date = existing.get("meta", {}).get("release_date")
            existing_family = existing.get("family")
            if creator and existing_creator and creator != existing_creator:
                return err(f"aa_public_model_catalog.json: conflicting creators for {canonical_id}")
            if release_date and existing_date and release_date != existing_date:
                return err(f"aa_public_model_catalog.json: conflicting release dates for {canonical_id}")
            if family and existing_family and family != existing_family:
                return err(f"aa_public_model_catalog.json: conflicting families for {canonical_id}")
            _merge_fill_nulls(out[canonical_id], record)
        else:
            out[canonical_id] = record
    return ok(out)


def _public_model_family(release, model_slug):
    if release is None:
        return ok(None)
    if not isinstance(release, dict):
        return err(f"aa_public_model_catalog.json: invalid release for {model_slug}")
    slug = release.get("slug")
    name = release.get("name")
    if slug is None and name is None:
        return ok(None)
    if not isinstance(slug, str) or not slug.strip():
        return err(f"aa_public_model_catalog.json: invalid family slug for {model_slug}")
    if not isinstance(name, str) or not name.strip():
        return err(f"aa_public_model_catalog.json: invalid family name for {model_slug}")
    return ok({"slug": slug, "name": name})


def _ensure_aa_record(out: dict, slug: str):
    if not slug:
        return None
    cid = resolve_from_slug(slug)
    if not cid:
        return None
    out.setdefault(cid, {
        "id": cid, "name": None, "creator": None, "model_type": None,
        "meta": {"release_date": None},
        "pricing": {"aa": {
            "inp_price": None, "out_price": None, "blended": None,
            "cache_hit_price": None, "cost_per_task": None,
            "speed_tps": None, "reasoning_tax_pct": None,
            "cost_segments": None,
        }},
        "benchmarks": {"aa": {
            "intel": None, "finance_accounting_index": None,
            "analyst_agent_pass_5": None, "briefcase_elo": None,
            "gdpval_elo": None, "omniscience_index": None,
            "time_per_task": None,
        }},
        "aliases": {"aa": slug},
    })
    return cid


def _jsonld_entries(datasets, name):
    by_name = {ds.get("name"): ds for ds in datasets if isinstance(ds, dict)}
    return by_name.get(name, {}).get("data", [])


def _slug_of(entry):
    return (entry.get("detailsUrl") or "").replace("/models/", "")


def _prop_vals(entry, field):
    """Extract a list of PropertyValue {name,value} from a JSON-LD field."""
    raw = entry.get(field, [])
    if isinstance(raw, list):
        return {pv.get("name"): pv.get("value") for pv in raw if isinstance(pv, dict)}
    return {}


def get_aa_jsonld_models(aa_dir: str):
    path = os.path.join(aa_dir, "aa_jsonld_export.json")
    if not os.path.exists(path):
        return ok({})
    loaded = _load_json(path)
    if loaded.is_err():
        return err(loaded.error)
    datasets = loaded.unwrap()
    if not isinstance(datasets, list):
        return err("aa_jsonld_export.json: expected a Dataset list")

    out: dict[str, dict] = {}
    intel_name = next((name for name in (
        "Artificial Analysis Intelligence Index by Open Weights / Proprietary",
        "Artificial Analysis Intelligence Index",
    ) if _jsonld_entries(datasets, name)), None)
    for entry in _jsonld_entries(datasets, intel_name) if intel_name else []:
        cid = _ensure_aa_record(out, _slug_of(entry))
        if cid:
            record = out[cid]
            record["name"] = record["name"] or entry.get("label")
            record["benchmarks"]["aa"]["intel"] = entry.get("intelligenceIndex")

    for dataset_name, source_field in (("Output Speed", "outputSpeed"), ("Speed", "medianOutputSpeed")):
        for entry in _jsonld_entries(datasets, dataset_name):
            cid = _ensure_aa_record(out, _slug_of(entry))
            if cid and out[cid]["pricing"]["aa"]["speed_tps"] is None:
                out[cid]["pricing"]["aa"]["speed_tps"] = entry.get(source_field)

    for entry in _jsonld_entries(datasets, "Cost per Task"):
        cid = _ensure_aa_record(out, _slug_of(entry))
        if cid:
            out[cid]["pricing"]["aa"]["cost_per_task"] = entry.get("costPerIntelligenceIndexTask")

    benchmark_sources = (
        ("Artificial Analysis Finance & Accounting Index", "finance_accounting_index", "score"),
        ("AA-AnalystAgent pass^5", "analyst_agent_pass_5", "analystAgent"),
        ("AA-Omniscience Index", "omniscience_index", "omniscienceIndex"),
        ("Time per Intelligence Index Task", "time_per_task", "timePerTask"),
    )
    for dataset_name, field, source_field in benchmark_sources:
        for entry in _jsonld_entries(datasets, dataset_name):
            cid = _ensure_aa_record(out, _slug_of(entry))
            if cid:
                out[cid]["benchmarks"]["aa"][field] = entry.get(source_field)

    for entry in _jsonld_entries(datasets, "AA-Briefcase Elo"):
        cid = _ensure_aa_record(out, _slug_of(entry))
        if cid:
            out[cid]["benchmarks"]["aa"]["briefcase_elo"] = _prop_vals(entry, "aaBriefcaseElo").get("mid")

    for entry in _jsonld_entries(datasets, "GDPval-AA v2.1 Leaderboard"):
        cid = _ensure_aa_record(out, _slug_of(entry))
        if cid:
            out[cid]["benchmarks"]["aa"]["gdpval_elo"] = _prop_vals(entry, "gdpvalAaElo").get("mid")

    for entry in _jsonld_entries(datasets, "Cost per Intelligence Index Task"):
        cid = _ensure_aa_record(out, _slug_of(entry))
        if not cid:
            continue
        aa = out[cid]["pricing"]["aa"]
        aa["cost_segments"] = {
            "total_cost_per_task_usd": aa.get("cost_per_task"),
            "answer_usd": entry.get("answer"),
            "reasoning_usd": entry.get("reasoning"),
            "cache_write_usd": entry.get("cacheWrite"),
            "cache_hit_usd": entry.get("cacheHit"),
            "input_usd": entry.get("input"),
        }

    for entry in _jsonld_entries(datasets, "Pricing: Cache Hit, Input, and Output"):
        cid = _ensure_aa_record(out, _slug_of(entry))
        if not cid:
            continue
        prices = _prop_vals(entry, "pricing")
        aa = out[cid]["pricing"]["aa"]
        if aa.get("inp_price") is None:
            aa["inp_price"] = prices.get("inputPrice")
        if aa.get("out_price") is None:
            aa["out_price"] = prices.get("outputPrice")

    return ok(out)


def get_aa_charts_models(aa_dir: str):
    from ._parse_charts import parse_aa_charts

    path = os.path.join(aa_dir, "aa_charts_export.json")
    if not os.path.exists(path):
        return ok({})
    parsed = parse_aa_charts(path)
    if parsed.is_err():
        return err(parsed.error)
    charts = parsed.unwrap()
    out: dict[str, dict] = {}

    for chart_key, field in (
        ("intel", "intel"),
        ("finance_accounting_index", "finance_accounting_index"),
        ("analyst_agent_pass_5", "analyst_agent_pass_5"),
        ("briefcase_elo", "briefcase_elo"),
        ("gdpval_elo", "gdpval_elo"),
        ("omniscience_index", "omniscience_index"),
        ("time_per_task", "time_per_task"),
    ):
        for slug, value in charts.get(chart_key, []):
            cid = _ensure_aa_record(out, slug)
            if cid:
                out[cid]["benchmarks"]["aa"][field] = value

    for slug, value in charts.get("cost_per_task", []):
        cid = _ensure_aa_record(out, slug)
        if not cid:
            continue
        aa = out[cid]["pricing"]["aa"]
        aa["cost_per_task"] = value
        aa["cost_segments"] = {
            "total_cost_per_task_usd": value,
            "answer_usd": None,
            "reasoning_usd": None,
            "cache_write_usd": None,
            "cache_hit_usd": None,
            "input_usd": None,
        }

    for slug, value in charts.get("output_speed", []):
        cid = _ensure_aa_record(out, slug)
        if cid:
            out[cid]["pricing"]["aa"]["speed_tps"] = value

    for slug, prices in charts.get("pricing", []):
        cid = _ensure_aa_record(out, slug)
        if not cid:
            continue
        pricing = out[cid]["pricing"]["aa"]
        if isinstance(prices, dict):
            if pricing.get("inp_price") is None and prices.get("inp") is not None:
                pricing["inp_price"] = prices["inp"]
            if pricing.get("out_price") is None and prices.get("out") is not None:
                pricing["out_price"] = prices["out"]
            if pricing.get("cache_hit_price") is None and prices.get("cache_hit") is not None:
                pricing["cache_hit_price"] = prices["cache_hit"]
            if pricing.get("blended") is None and pricing.get("inp_price") is not None and pricing.get("out_price") is not None:
                pricing["blended"] = round((pricing["inp_price"] + 3 * pricing["out_price"]) / 4, 6)

    return ok(out)


def _step_charts(all_models: dict, aa_dir: str):
    charts = get_aa_charts_models(aa_dir)
    if charts.is_err():
        return err(charts.error)
    for cid, record in charts.unwrap().items():
        all_models.setdefault(cid, record)
    return ok(all_models)


def _step_jsonld(all_models: dict, aa_dir: str):
    jsonld = get_aa_jsonld_models(aa_dir)
    if jsonld.is_err():
        return err(jsonld.error)
    for cid, record in jsonld.unwrap().items():
        if cid in all_models:
            _merge_fill_nulls(all_models[cid], record)
        else:
            all_models[cid] = record
    return ok(all_models)


def _step_metadata(all_models: dict, aa_dir: str):
    metadata = get_aa_metadata(aa_dir)
    if metadata.is_err():
        return err(metadata.error)
    for cid, record in metadata.unwrap().items():
        if cid in all_models:
            _merge_fill_nulls(all_models[cid], record)
    return ok(all_models)


def _step_public_model_catalog(all_models: dict, aa_dir: str):
    catalog = get_aa_public_model_catalog(aa_dir)
    if catalog.is_err():
        return err(catalog.error)
    for canonical_id, record in catalog.unwrap().items():
        if canonical_id in all_models:
            _merge_fill_nulls(all_models[canonical_id], record)
    return ok(all_models)


def _derive_reasoning_tax(all_models: dict) -> dict:
    for model in all_models.values():
        aa = model.get("pricing", {}).get("aa", {})
        segments = aa.get("cost_segments") or {}
        total = aa.get("cost_per_task")
        if total is None:
            total = segments.get("total_cost_per_task_usd")
        reasoning = segments.get("reasoning_usd")
        if total is not None and total > 0 and reasoning is not None:
            aa["reasoning_tax_pct"] = round(reasoning / total * 100, 1)
    return all_models


def get_aa_models(base: Path):
    aa_dir = os.path.join(base, "data", "sources", "aa")
    missing = [filename for filename in ("aa_charts_export.json", "aa_jsonld_export.json")
               if not os.path.exists(os.path.join(aa_dir, filename))]
    if missing:
        return err(f"Missing AA primary export(s): {', '.join(missing)}")
    all_models: dict[str, dict] = {}

    for step in (_step_charts, _step_jsonld, _step_metadata, _step_public_model_catalog):
        result = step(all_models, aa_dir)
        if result.is_err():
            return err(result.error)
        all_models = result.unwrap()

    for model in all_models.values():
        if not model.get("name"):
            model["name"] = model["aliases"]["aa"]

    if not all_models:
        return err("AA primary exports contained no recognized model data")

    return ok(_derive_reasoning_tax(all_models))



def _merge_fill_nulls(existing: dict, incoming: dict) -> None:
    for key, val in incoming.items():
        if key not in existing:
            existing[key] = val
            continue
        ev = existing[key]
        if isinstance(ev, dict) and isinstance(val, dict):
            _merge_fill_nulls(ev, val)
        elif ev is None and val is not None:
            existing[key] = val
