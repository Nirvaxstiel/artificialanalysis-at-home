
import json, os, re
from pathlib import Path

from ..._canonical import resolve_from_slug, costbd_name_to_canonical
from _result import ok, err


def _load_json(path: str):
    """Read + parse a JSON source file. Ok(dict) or Err(reason)."""
    try:
        with open(path) as f:
            return ok(json.load(f))
    except (OSError, json.JSONDecodeError) as e:  # noqa: BLE001
        return err(f"{os.path.basename(path)}: {e}")


def get_aa_live_models(aa_dir: str) -> dict[str, dict]:
    """Live AA API pull (aa_api_live.json): 551 models with release_date + creator.

    Used to enrich release_date into meta and backfill creator where the static
    scraped set left it null. Source of truth for 'when did this model ship'.
    """
    path = os.path.join(aa_dir, "aa_api_live.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        payload = json.load(f)
    out: dict[str, dict] = {}
    for m in payload.get("data", []):
        slug = m.get("slug")
        if not slug:
            continue
        creator = (m.get("model_creator") or {}).get("name")
        out[slug] = {
            "release_date": m.get("release_date"),
            "creator": creator,
            "evaluations": m.get("evaluations", {}),
        }
    return out


def _ensure_aa_record(out: dict, slug: str):
    """Create the base AA record for a slug if not present; return cid or None.

    Emits the FULL pricing.aa / benchmarks.aa schema (all known keys, None) so
    downstream overlays (_overlay_enriched, _overlay_aa_api) that do direct
    key access never KeyError on a JSON-LD-only (partial) record.
    """
    if not slug:
        return None
    cid = resolve_from_slug(slug)
    if not cid:
        return None
    out.setdefault(cid, {
        "id": cid, "name": None, "creator": None, "model_type": None,
        "meta": {"archetype": None, "pareto_optimal": False, "has_breakdown": False,
                 "cost_percentile": None, "iq_percentile": None, "release_date": None},
        "pricing": {"aa": {
            "inp_price": None, "out_price": None, "blended": None,
            "cache_hit_price": None, "cost_per_task": None, "tokens_m": None,
            "speed_tps": None, "useful_cost": None, "reasoning_tax_pct": None,
            "cost_segments": None,
        }},
        "benchmarks": {"aa": {
            "intel": None, "iq_per_dollar": None, "iq_per_mtok": None,
            "iq_per_mtokdollar": None, "aa_coding_index": None,
            "aa_math_index": None, "gpqa": None, "mmlu_pro": None, "hle": None,
            "aime": None, "aime_25": None, "math_500": None, "livecodebench": None,
            "ifbench": None, "lcr": None, "scicode": None, "tau2": None,
            "tau_banking": None, "terminalbench_hard": None,
            "terminalbench_v2_1": None, "omniscience_hallucination_rate": None,
            "briefcase_analytical_quality_elo": None,
            "briefcase_presentation_elo": None, "time_per_task": None,
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


def get_aa_jsonld_models(aa_dir: str) -> dict[str, dict]:
    """AA JSON-LD Dataset export (console query) → canonical_id → model record.

    Source: data/sources/aa/aa_jsonld_export.json (schema.org Dataset objects
    the AA site exposes; the 'real way to query' per the user — no scraping/vision).
    Each dataset has `data[]` entries keyed by `label` + `detailsUrl` (→ slug).

    Maps JSON-LD metrics onto the `aa.*` contract:
      intelligenceIndex / artificialAnalysisIntelligenceIndex → benchmarks.aa.intel
      medianOutputSpeed → pricing.aa.speed_tps
      costPerIntelligenceIndexTask → pricing.aa.cost_per_task
      codingIndex → benchmarks.aa.aa_coding_index
      omniscienceHallucinationRate → benchmarks.aa.omniscience_hallucination_rate
      aaBriefcaseQualityElos[] → benchmarks.aa.briefcase_*_elo
      timePerTask → benchmarks.aa.time_per_task
      Cost to Run AA Intelligence Index (5 fields) → pricing.aa.cost_segments.*
      pricing[] (inputPrice/outputPrice) → pricing.aa.inp_price/out_price

    The two intelligence datasets are value-identical (asserted in tests); the
    Open-Weights/Proprietary one is the superset, so only it feeds `intel`.
    """
    path = os.path.join(aa_dir, "aa_jsonld_export.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        datasets = json.load(f)

    out: dict[str, dict] = {}

    # Intelligence (use Open-Weights/Proprietary superset only)
    for e in _jsonld_entries(datasets, "Artificial Analysis Intelligence Index by Open Weights / Proprietary"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid:
            continue
        rec = out[cid]
        if rec["name"] is None:
            rec["name"] = e.get("label")
        if rec["benchmarks"]["aa"].get("intel") is None:
            rec["benchmarks"]["aa"]["intel"] = e.get("intelligenceIndex")

    # Speed
    for e in _jsonld_entries(datasets, "Speed"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid or out[cid]["pricing"]["aa"].get("speed_tps") is not None:
            continue
        out[cid]["pricing"]["aa"]["speed_tps"] = e.get("medianOutputSpeed")

    # Cost per Task
    for e in _jsonld_entries(datasets, "Cost per Task"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid or out[cid]["pricing"]["aa"].get("cost_per_task") is not None:
            continue
        out[cid]["pricing"]["aa"]["cost_per_task"] = e.get("costPerIntelligenceIndexTask")

    # Coding Index
    for e in _jsonld_entries(datasets, "Artificial Analysis Coding Index"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if out[cid]["benchmarks"]["aa"].get("aa_coding_index") is not None:
            continue
        out[cid]["benchmarks"]["aa"]["aa_coding_index"] = e.get("codingIndex")

    # Omniscience Hallucination Rate
    for e in _jsonld_entries(datasets, "AA-Omniscience Hallucination Rate"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid or out[cid]["benchmarks"]["aa"].get("omniscience_hallucination_rate") is not None:
            continue
        out[cid]["benchmarks"]["aa"]["omniscience_hallucination_rate"] = e.get("omniscienceHallucinationRate")

    # Briefcase Elo (analyticalQuality / presentation, mid value)
    for e in _jsonld_entries(datasets, "AA-Briefcase Analytical Quality & Presentation Elo"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid:
            continue
        pvs = _prop_vals(e, "aaBriefcaseQualityElos")
        b = out[cid]["benchmarks"]["aa"]
        for src, dst in (("analyticalQuality mid", "briefcase_analytical_quality_elo"),
                         ("presentation mid", "briefcase_presentation_elo")):
            if b.get(dst) is None and pvs.get(src) is not None:
                b[dst] = pvs.get(src)

    # Time per Task
    for e in _jsonld_entries(datasets, "Time per Intelligence Index Task"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid or out[cid]["benchmarks"]["aa"].get("time_per_task") is not None:
            continue
        out[cid]["benchmarks"]["aa"]["time_per_task"] = e.get("timePerTask")

    # Cost breakdown (5 segments) — descriptive only.
    # NOTE: do NOT derive cost_per_task here. This "Cost to Run Intelligence Index"
    # dataset reports the cost to run the ENTIRE benchmark as one job (full-index
    # token volume), which hits $100s+ for reasoning models — NOT a per-task cost.
    # cost_per_task comes from the "Cost per Task" dataset (above) + aa_cost_breakdown
    # (Step 3), both sane per-task values. Using this dataset's sum would inflate
    # cost_per_task 100-1000x and break the cost-efficiency axis.
    for e in _jsonld_entries(datasets, "Cost to Run Artificial Analysis Intelligence Index"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid:
            continue
        aa = out[cid]["pricing"]["aa"]
        segs = {
            "answer_usd": e.get("answerCost"),
            "reasoning_usd": e.get("reasoningCost"),
            "cache_write_usd": e.get("cacheWriteCost"),
            "cache_hit_usd": e.get("cacheReadCost"),
            "input_usd": e.get("nonCacheInputCost"),
        }
        if any(v is not None for v in segs.values()):
            aa["cost_segments"] = segs

    # Pricing (input/output per M tokens)
    for e in _jsonld_entries(datasets, "Pricing: Cache Hit, Input, and Output"):
        cid = _ensure_aa_record(out, _slug_of(e))
        if not cid:
            continue
        pvs = _prop_vals(e, "pricing")
        aa = out[cid]["pricing"]["aa"]
        if aa.get("inp_price") is None and pvs.get("inputPrice") is not None:
            aa["inp_price"] = pvs.get("inputPrice")
        if aa.get("out_price") is None and pvs.get("outputPrice") is not None:
            aa["out_price"] = pvs.get("outputPrice")

    return out


def get_aa_charts_models(aa_dir: str) -> dict[str, dict]:
    """AA method-2 SVG scrape (browser console query) → canonical_id → model record.

    Source: data/sources/aa/aa_charts_export.json (16 chart SVGs). Parsed by
    _parse_charts.parse_aa_charts → {chart_key: [(slug, value), ...]}.

    Reliable charts ingested here (method-2 is a SUPERSET of the JSON-LD export
    for these — 58-106 models vs 10-20):
      coding_index        → benchmarks.aa.aa_coding_index
      intel               → benchmarks.aa.intel
      briefcase           → benchmarks.aa.briefcase_analytical_quality_elo / _presentation_elo
      time_per_task       → benchmarks.aa.time_per_task
      omniscience         → benchmarks.aa.omniscience_hallucination_rate (89% → 0.89)
      pricing (#9)        → pricing.aa.inp_price / out_price / cache_hit_price
                          (x-aligned 3-series parse; validated vs live API)

    Deferred (SVG lacks clean per-model series alignment → ambiguous):
      cost_to_run (#8) — 6 label-list groups at divergent x-ranges; mapping its
      $X to cost_segments.* would be guesswork. Source cost segments from
      aa_cost_breakdown.json instead (handled in Step 3).
    """
    from ._parse_charts import parse_aa_charts

    path = os.path.join(aa_dir, "aa_charts_export.json")
    if not os.path.exists(path):
        return {}
    charts = parse_aa_charts(path).unwrap_or({})

    out: dict[str, dict] = {}

    for slug, val in charts.get("coding_index", []):
        cid = _ensure_aa_record(out, slug)
        if cid and out[cid]["benchmarks"]["aa"].get("aa_coding_index") is None:
            out[cid]["benchmarks"]["aa"]["aa_coding_index"] = val

    for slug, val in charts.get("intel", []):
        cid = _ensure_aa_record(out, slug)
        if cid and out[cid]["benchmarks"]["aa"].get("intel") is None:
            out[cid]["benchmarks"]["aa"]["intel"] = val

    for slug, vals in charts.get("briefcase", []):
        cid = _ensure_aa_record(out, slug)
        if not cid:
            continue
        b = out[cid]["benchmarks"]["aa"]
        if isinstance(vals, list) and len(vals) >= 2:
            if b.get("briefcase_analytical_quality_elo") is None:
                b["briefcase_analytical_quality_elo"] = vals[0]
            if b.get("briefcase_presentation_elo") is None:
                b["briefcase_presentation_elo"] = vals[1]

    for slug, val in charts.get("time_per_task", []):
        cid = _ensure_aa_record(out, slug)
        if cid and out[cid]["benchmarks"]["aa"].get("time_per_task") is None:
            out[cid]["benchmarks"]["aa"]["time_per_task"] = val

    for slug, val in charts.get("omniscience", []):
        cid = _ensure_aa_record(out, slug)
        if cid and out[cid]["benchmarks"]["aa"].get("omniscience_hallucination_rate") is None:
            out[cid]["benchmarks"]["aa"]["omniscience_hallucination_rate"] = val

    for slug, prices in charts.get("pricing", []):
        cid = _ensure_aa_record(out, slug)
        if not cid:
            continue
        p = out[cid]["pricing"]["aa"]
        if isinstance(prices, dict):
            if p.get("inp_price") is None and prices.get("inp") is not None:
                p["inp_price"] = prices["inp"]
            if p.get("out_price") is None and prices.get("out") is not None:
                p["out_price"] = prices["out"]
            if p.get("cache_hit_price") is None and prices.get("cache_hit") is not None:
                p["cache_hit_price"] = prices["cache_hit"]
            # blended (AA "3-to-1" = (input + 3·output)/4) derived from sourced inp/out
            if p.get("blended") is None and p.get("inp_price") is not None and p.get("out_price") is not None:
                p["blended"] = round((p["inp_price"] + 3 * p["out_price"]) / 4, 6)

    return out


def _step_charts(all_models: dict, aa_dir: str) -> dict:
    """Stage 0 — AA method-2 SVG scrape seeds NEW models + the SUPERSET of aa.*."""
    charts = get_aa_charts_models(aa_dir)
    for cid, rec in charts.items():
        all_models.setdefault(cid, rec)
    return all_models


def _step_jsonld(all_models: dict, aa_dir: str) -> dict:
    """Stage 0b — AA JSON-LD console query fills gaps the charts don't cover."""
    jsonld = get_aa_jsonld_models(aa_dir)
    for cid, rec in jsonld.items():
        if cid not in all_models:
            all_models.setdefault(cid, rec)
        else:
            _merge_fill_nulls(all_models[cid], rec)
    return all_models


def _step_scraped(all_models: dict, aa_dir: str) -> "Ok[dict]|Err[str]":
    """Stage 1 — base 99 AA models from the static scrape; JSON-LD-seeded fields survive."""
    scraped = _load_json(os.path.join(aa_dir, "raw", "aa_models_scraped.json"))
    if scraped.is_err():
        return err(scraped.error)
    scraped_models = scraped.unwrap()

    seen_slugs = set()
    for m in scraped_models:
        slug = m.get("slug")
        if slug and slug in seen_slugs:
            print(f"  ⚠ Duplicate AA slug '{slug}' in aa_models_scraped.json — overwriting previous")
        seen_slugs.add(slug)

    live_models = get_aa_live_models(aa_dir)

    for m in scraped_models:
        slug = m.get("slug")
        cid = resolve_from_slug(slug)
        if not cid:
            continue
        live = live_models.get(slug, {})
        live_eval = live.get("evaluations", {})

        scraped_record = {
            "id": cid,
            "name": m.get("name"),
            "creator": m.get("creator") or live.get("creator"),
            "model_type": "reasoning" if m.get("is_reasoning") else None,
            "meta": {
                "archetype": None,
                "pareto_optimal": False,
                "cost_percentile": None,
                "iq_percentile": None,
                "has_breakdown": False,
                "release_date": live.get("release_date"),
            },
            "pricing": {
                "aa": {
                    "inp_price": m.get("input_price"),
                    "out_price": m.get("output_price"),
                    "blended": None,
                    "cache_hit_price": m.get("cache_hit_price"),
                    "cost_per_task": None,
                    "tokens_m": None,
                    "speed_tps": m.get("speed_tps"),
                    "useful_cost": None,
                    "reasoning_tax_pct": None,
                }
            },
            "benchmarks": {
                "aa": {
                    "intel": m.get("intelligence") or live_eval.get("artificial_analysis_intelligence_index"),
                    "iq_per_dollar": None,
                    "iq_per_mtok": None,
                    "iq_per_mtokdollar": None,
                    "aa_coding_index": live_eval.get("artificial_analysis_coding_index"),
                    "aa_math_index": live_eval.get("artificial_analysis_math_index"),
                    "gpqa": live_eval.get("gpqa"),
                    "mmlu_pro": live_eval.get("mmlu_pro"),
                    "hle": live_eval.get("hle"),
                    "aime": live_eval.get("aime"),
                    "aime_25": live_eval.get("aime_25"),
                    "math_500": live_eval.get("math_500"),
                    "livecodebench": live_eval.get("livecodebench"),
                    "ifbench": live_eval.get("ifbench"),
                    "lcr": live_eval.get("lcr"),
                    "scicode": live_eval.get("scicode"),
                    "tau2": live_eval.get("tau2"),
                    "tau_banking": live_eval.get("tau_banking"),
                    "terminalbench_hard": live_eval.get("terminalbench_hard"),
                    "terminalbench_v2_1": live_eval.get("terminalbench_v2_1"),
                }
            },
            "aliases": {
                "aa": slug,
            },
        }
        if cid in all_models:
            _merge_fill_nulls(all_models[cid], scraped_record)
        else:
            all_models[cid] = scraped_record

    return ok(all_models)


def _step_live_api(all_models: dict, base: Path) -> dict:
    """Stage 1.5 — fill nulls from the authoritative live AA API."""
    api_models = _load_aa_api(base)
    if api_models:
        for cid, model in all_models.items():
            api_slug = model.get("aliases", {}).get("aa")
            aa_m = api_models.get(api_slug) if api_slug else None
            if aa_m:
                _overlay_aa_api(model, aa_m)
    return all_models


def _step_enriched(all_models: dict, aa_dir: str) -> "Ok[dict]|Err[str]":
    """Stage 2 — enrich from aa_model_data.json (blended, tokens_m, etc.)."""
    enriched = _load_json(os.path.join(aa_dir, "enriched", "aa_model_data.json"))
    if enriched.is_err():
        return err(enriched.error)
    aa_raw = enriched.unwrap()

    for slug, raw in aa_raw.items():
        cid = resolve_from_slug(slug)
        if not cid:
            continue
        if cid not in all_models:
            all_models[cid] = _make_model_from_enriched(slug, cid, raw)
        else:
            _overlay_enriched(all_models[cid], raw)

    return ok(all_models)


def _step_cost_breakdown(all_models: dict, aa_dir: str) -> "Ok[dict]|Err[str]":
    """Stage 3 — cost segments from aa_cost_breakdown.json (optional; short-circuits if absent)."""
    costbd = _load_json(os.path.join(aa_dir, "enriched", "aa_cost_breakdown.json")).unwrap_or(None)
    if costbd is None:
        return ok(all_models)

    for m in costbd.get("models", []):
        display_name = m.get("name", "")
        cid = costbd_name_to_canonical(display_name).unwrap_or(None)
        if not cid or cid not in all_models:
            continue

        pricing = all_models[cid].setdefault("pricing", {})
        aa = pricing.setdefault("aa", {})
        seg_total = m.get("total_cost_per_task_usd")
        aa["cost_segments"] = {
            "total_cost_per_task_usd": seg_total,
            "answer_usd": m.get("answer_usd"),
            "reasoning_usd": m.get("reasoning_usd"),
            "cache_write_usd": m.get("cache_write_usd"),
            "cache_hit_usd": m.get("cache_hit_usd"),
            "input_usd": m.get("input_usd"),
        }
        if seg_total is not None:
            aa["cost_per_task"] = seg_total
            reasoning = m.get("reasoning_usd")
            if reasoning is not None and seg_total > 0:
                aa["reasoning_tax_pct"] = round(reasoning / seg_total * 100, 1)

    return ok(all_models)


def get_aa_models(base: Path) -> dict[str, dict]:
    """Merge all AA data sources into dict of canonical_id → model record.

    Sources (in order of priority — later sources enrich but don't overwrite
    non-null fields from earlier sources):
      0. data/sources/aa/aa_charts_export.json — AA method-2 SVG scrape (NEW models + superset aa.*)
      0b. data/sources/aa/aa_jsonld_export.json — AA JSON-LD console query (fallback for charts not yet scraped)
      1. data/sources/aa/raw/aa_models_scraped.json  — 99 base AA models
      2. data/sources/aa/enriched/aa_model_data.json  — enriched fields (38 models)
      3. data/sources/aa/enriched/aa_cost_breakdown.json — cost segments (30 models)
    """
    AA_DIR = os.path.join(base, "data", "sources", "aa")
    all_models: dict[str, dict] = {}

    all_models = _step_charts(all_models, AA_DIR)
    all_models = _step_jsonld(all_models, AA_DIR)

    r = _step_scraped(all_models, AA_DIR)
    if r.is_err():
        return err(r.error)
    all_models = r.unwrap()

    all_models = _step_live_api(all_models, base)

    r = _step_enriched(all_models, AA_DIR)
    if r.is_err():
        return err(r.error)
    all_models = r.unwrap()

    r = _step_cost_breakdown(all_models, AA_DIR)
    if r.is_err():
        return err(r.error)
    all_models = r.unwrap()

    return ok(all_models)



def _make_model_from_enriched(slug: str, cid: str, raw: dict) -> dict:
    """Build a model record from enriched data when no scraped base exists."""
    return {
        "id": cid,
        "name": raw.get("name"),
        "creator": raw.get("creator"),
        "model_type": None,
        "meta": {
            "archetype": None,
            "pareto_optimal": False,
            "cost_percentile": None,
            "iq_percentile": None,
            "has_breakdown": False,
        },
        "pricing": {
            "aa": {
                "inp_price": raw.get("inp"),
                "out_price": raw.get("out"),
                "blended": raw.get("blended"),
                "cache_hit_price": raw.get("cache"),
                "cost_per_task": None,
                "tokens_m": raw.get("tokens_m"),
                "speed_tps": raw.get("spd"),
                "useful_cost": raw.get("eff_cost_per_m"),
                "reasoning_tax_pct": None,
            }
        },
        "benchmarks": {
            "aa": {
                "intel": raw.get("intel"),
                "iq_per_dollar": (raw.get("iq_per_1k") / 1000.0) if raw.get("iq_per_1k") is not None else None,
                "iq_per_mtok": None,
                "iq_per_mtokdollar": raw.get("cost_per_iq"),
            }
        },
        "aliases": {
            "aa": slug,
        }
    }


def _overlay_aa_api(model: dict, aa_m: dict) -> None:
    """Fill null AA fields from live AA API response (nulls only — no override)."""
    ev = aa_m.get("evaluations", {}) or {}
    pr = aa_m.get("pricing", {}) or {}
    p = model.setdefault("pricing", {}).setdefault("aa", {})
    b = model.setdefault("benchmarks", {}).setdefault("aa", {})

    if model.get("creator") is None:
        creator = (aa_m.get("model_creator") or {}).get("name")
        if creator:
            model["creator"] = creator
    if model.get("meta", {}).get("release_date") is None:
        rd = aa_m.get("release_date")
        if rd:
            model.setdefault("meta", {})["release_date"] = rd

    fills = [
        (p, {
            "inp_price": pr.get("price_1m_input_tokens"),
            "out_price": pr.get("price_1m_output_tokens"),
            "blended": pr.get("price_1m_blended_3_to_1"),
            "speed_tps": aa_m.get("median_output_tokens_per_second"),
            "ttft": aa_m.get("median_time_to_first_token_seconds"),
        }),
        (b, {
            "intel": ev.get("artificial_analysis_intelligence_index"),
            "coding_index": ev.get("artificial_analysis_coding_index"),
            "math_index": ev.get("artificial_analysis_math_index"),
            "mmlu_pro": ev.get("mmlu_pro"),
            "gpqa": ev.get("gpqa"),
        }),
    ]
    for sec, kv in fills:
        for k, v in kv.items():
            if v is not None and sec.get(k) is None:
                sec[k] = v


def _load_aa_api(base: Path) -> dict:
    """Load live AA models: prefer the cached aa_api_live.json (gitignored workflow
    artifact from the aa-api-live-fill skill), fall back to a live HTTPS call using the
    Free-tier /free endpoint (the /data/llms/models path 403s even with a valid key)."""
    cache_path = os.path.join(base, "data", "sources", "aa", "aa_api_live.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                d = json.load(f)
            models = d.get("data") or d.get("models") or []
            return {m["slug"]: m for m in models if m.get("slug")}
        except (OSError, ValueError):
            pass

    key = os.environ.get("AA_API_KEY")
    if not key:
        env_path = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AA_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except OSError:
            pass
    if not key:
        return {}
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://artificialanalysis.ai/api/v2/language/models/free",
            headers={"x-api-key": key, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data") or data.get("models") or []
        return {m["slug"]: m for m in models if m.get("slug")}
    except Exception:
        return {}


def _merge_fill_nulls(existing: dict, incoming: dict) -> None:
    """Merge `incoming` into `existing` fill-nulls-only (existing non-null wins).

    Recurses into nested dicts (benchmarks.aa, pricing.aa) so deep fields like
    aa_math_index / cost_segments survive. Used so JSON-LD/charts-seeded fields
    persist when the scraped base loop would otherwise hard-overwrite the record.
    """
    for key, val in incoming.items():
        if key not in existing:
            existing[key] = val
            continue
        ev = existing[key]
        if isinstance(ev, dict) and isinstance(val, dict):
            _merge_fill_nulls(ev, val)
        elif ev is None and val is not None:
            existing[key] = val


def _overlay_enriched(model: dict, raw: dict) -> None:
    """Overlay enriched fields onto an existing scraped-model entry (fill nulls only)."""
    p = model["pricing"]["aa"]
    b = model["benchmarks"]["aa"]
    if p["inp_price"] is None:
        p["inp_price"] = raw.get("inp")
    if p["out_price"] is None:
        p["out_price"] = raw.get("out")
    if p["blended"] is None:
        p["blended"] = raw.get("blended")
    if p["cache_hit_price"] is None:
        p["cache_hit_price"] = raw.get("cache")
    if p["speed_tps"] is None:
        p["speed_tps"] = raw.get("spd")
    if p["tokens_m"] is None:
        p["tokens_m"] = raw.get("tokens_m")
    if p["useful_cost"] is None:
        p["useful_cost"] = raw.get("eff_cost_per_m")
    if b["intel"] is None:
        b["intel"] = raw.get("intel")
    if b["iq_per_dollar"] is None and raw.get("iq_per_1k") is not None:
        b["iq_per_dollar"] = raw.get("iq_per_1k") / 1000.0
    if b["iq_per_mtokdollar"] is None:
        b["iq_per_mtokdollar"] = raw.get("cost_per_iq")
