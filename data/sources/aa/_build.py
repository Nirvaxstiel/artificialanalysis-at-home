
import json, os, re
from pathlib import Path

from ..._canonical import resolve_from_slug, costbd_name_to_canonical


def get_aa_models(base: Path) -> dict[str, dict]:
    """Merge all AA data sources into dict of canonical_id → model record.

    Sources (in order of priority — later sources enrich but don't overwrite
    non-null fields from earlier sources):
      1. data/sources/aa/raw/aa_models_scraped.json  — 99 base AA models
      2. data/sources/aa/enriched/aa_model_data.json  — enriched fields (38 models)
      3. data/sources/aa/enriched/aa_cost_breakdown.json — cost segments (30 models)
    """
    AA_DIR = os.path.join(base, "data", "sources", "aa")
    all_models: dict[str, dict] = {}

    # === 1) Base: raw scraped data ===
    scraped_path = os.path.join(AA_DIR, "raw", "aa_models_scraped.json")
    with open(scraped_path) as f:
        scraped_models = json.load(f)

    # Warn on duplicate slugs
    seen_slugs = set()
    for m in scraped_models:
        slug = m.get("slug")
        if slug and slug in seen_slugs:
            print(f"  ⚠ Duplicate AA slug '{slug}' in aa_models_scraped.json — overwriting previous")
        seen_slugs.add(slug)

    for m in scraped_models:
        slug = m.get("slug")
        cid = resolve_from_slug(slug)
        if not cid:
            continue

        all_models[cid] = {
            "id": cid,
            "name": m.get("name"),
            "creator": m.get("creator"),
            "model_type": "reasoning" if m.get("is_reasoning") else None,
            "meta": {
                "archetype": None,
                "pareto_optimal": False,
                "cost_percentile": None,
                "iq_percentile": None,
                "has_breakdown": False,
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
                    "intel": m.get("intelligence"),
                    "iq_per_dollar_pt": None,
                    "iq_per_mtok": None,
                    "iq_per_mtokdollar": None,
                }
            },
            "aliases": {
                "aa": slug,
            }
        }

    # === 1.5) Live AA API — fill nulls from authoritative source ===
    api_models = _load_aa_api()
    if api_models:
        for cid, model in all_models.items():
            api_slug = model.get("aliases", {}).get("aa")
            aa_m = api_models.get(api_slug) if api_slug else None
            if aa_m:
                _overlay_aa_api(model, aa_m)

    # === 2) Enrich from aa_model_data.json (blended, tokens_m, etc.) ===
    enriched_path = os.path.join(AA_DIR, "enriched", "aa_model_data.json")
    with open(enriched_path) as f:
        aa_raw = json.load(f)

    for slug, raw in aa_raw.items():
        cid = resolve_from_slug(slug)
        if not cid:
            continue

        if cid not in all_models:
            # Models only in enriched data (eg Mistral Medium 3.5)
            all_models[cid] = _make_model_from_enriched(slug, cid, raw)
        else:
            _overlay_enriched(all_models[cid], raw)

    # === 3) Cost segments from aa_cost_breakdown.json ===
    costbd_path = os.path.join(AA_DIR, "enriched", "aa_cost_breakdown.json")
    try:
        with open(costbd_path) as f:
            costbd_data = json.load(f)
    except FileNotFoundError:
        return all_models  # cost breakdown is optional

    for m in costbd_data.get("models", []):
        display_name = m.get("name", "")
        cid = costbd_name_to_canonical(display_name)
        if not cid or cid not in all_models:
            continue

        p = all_models[cid].setdefault("pricing", {})
        aa = p.setdefault("aa", {})
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

    return all_models


# ── helpers ──


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
                "iq_per_dollar_pt": None,
                "iq_per_mtok": raw.get("iq_per_1k"),
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


def _load_aa_api() -> dict:
    """Fetch live AA models via API; return slug→record. Empty if no key."""
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
            "https://artificialanalysis.ai/api/v2/data/llms/models",
            headers={"x-api-key": key, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = data.get("data") or data.get("models") or []
        out = {}
        for m in models:
            s = m.get("slug")
            if s:
                out[s] = m
        return out
    except Exception:
        return {}


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
    if b["iq_per_mtok"] is None:
        b["iq_per_mtok"] = raw.get("iq_per_1k")
    if b["iq_per_mtokdollar"] is None:
        b["iq_per_mtokdollar"] = raw.get("cost_per_iq")
