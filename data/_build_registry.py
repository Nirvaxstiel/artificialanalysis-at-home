import json, csv, os, re
from datetime import date
from pathlib import Path

from .sources.aa._build import get_aa_models
from .sources.aa.img._build import get_aa_img_models
from .sources.dirac._build import get_dirac_models
from ._canonical import (
    resolve_from_slug, livebench_name_to_canonical,
    openrouter_id_to_canonical, openllm_name_to_canonical,
    aa_img_name_to_canonical, costbd_name_to_canonical,
    canonical_to_or_id, resolve_or_context,
)
from ._domain._entities import RegistryModel


def _ensure(all_models, cid, **overrides):
    if cid not in all_models:
        all_models[cid] = {"id": cid, "name": None, "creator": None,
                           "model_type": None,
                           "meta": {}, "pricing": {},
                           "benchmarks": {}, "aliases": {},
                           **overrides}
    return all_models[cid]


def run(ctx=None):
    if ctx and ctx.get("root"):
        BASE = Path(ctx["root"])
    else:
        BASE = Path(__file__).resolve().parent.parent

    SRC = os.path.join(BASE, "data", "sources")
    OUT = os.path.join(BASE, "data", "model_registry.json")

    today = date.today().isoformat()
    all_models = {}  # canonical_id -> model record

    # ── AA (from data/sources/aa/_build.py) ──
    aa_models = get_aa_models(BASE)
    all_models.update(aa_models)

    # ── AA IMAGE CHARTS (vision-transcribed scalars) ──
    aa_img_models = get_aa_img_models(BASE)
    for cid, img in aa_img_models.items():
        if cid not in all_models:
            all_models[cid] = {"id": cid, "name": None, "creator": None,
                               "model_type": None, "meta": {}, "pricing": {},
                               "benchmarks": {}, "aliases": {}}
        existing = all_models[cid]
        img_b = img.get("benchmarks", {}).get("aa_img")
        if img_b:
            existing.setdefault("benchmarks", {}).setdefault("aa_img", {}).update(img_b)
        img_p = img.get("pricing", {}).get("aa")
        if img_p:
            ep = existing.setdefault("pricing", {}).setdefault("aa", {})
            for k, v in img_p.items():
                if v is not None and ep.get(k) is None:
                    ep[k] = v
        img_meta = img.get("meta", {})
        if img_meta:
            existing.setdefault("meta", {}).update(img_meta)

    # ── AA SCRAPE PROGRESS (provenance: which models were image-transcribed) ──
    scrape_path = os.path.join(SRC, "aa", "aa_scrape_progress.json")
    scraped_slugs = set()
    if os.path.exists(scrape_path):
        try:
            with open(scrape_path) as f:
                sp = json.load(f)
            scraped_slugs = set(sp.get("scraped", []))
        except (OSError, ValueError):
            pass
    for cid in aa_img_models:
        if cid in scraped_slugs:
            all_models.setdefault(cid, {}).setdefault("meta", {})["aa_img_scraped"] = True

    # ── DIRAC.RUN (observed cache hit rates, OpenRouter Effective Pricing) ──
    dirac_models = get_dirac_models(BASE)
    for cid, d in dirac_models.items():
        if cid not in all_models:
            all_models[cid] = {"id": cid, "name": None, "creator": None,
                               "model_type": None, "meta": {}, "pricing": {},
                               "benchmarks": {}, "aliases": {}}
        existing = all_models[cid]
        db = d.get("benchmarks", {}).get("dirac")
        if db:
            existing.setdefault("benchmarks", {}).setdefault("dirac", {}).update(db)
        dmeta = d.get("meta", {})
        if dmeta:
            existing.setdefault("meta", {}).update(dmeta)

    # ── LIVEBENCH ──
    lb_path = os.path.join(SRC, "livebench_2026_01_08.csv")
    cat_path = os.path.join(SRC, "livebench_categories_2026_01_08.json")

    with open(cat_path) as f:
        lb_categories = json.load(f)

    task_to_cat = {}
    for cat_name, tasks in lb_categories.items():
        for t in tasks:
            task_to_cat[t] = cat_name

    with open(lb_path) as f:
        reader = csv.DictReader(f)
        lb_models = list(reader)

    for m in lb_models:
        name = m["model"]
        cid = livebench_name_to_canonical(name)

        scores = {}
        cat_scores = {}
        task_count = 0
        for task, val in m.items():
            if task == "model":
                continue
            if val == "" or val is None:
                continue
            try:
                v = float(val)
            except (ValueError, TypeError):
                continue
            scores[task] = v

            cat = task_to_cat.get(task, "Other")
            if cat not in cat_scores:
                cat_scores[cat] = []
            cat_scores[cat].append(v)
            task_count += 1

        cat_avgs = {cat: round(sum(vs)/len(vs), 2) for cat, vs in cat_scores.items()}
        overall = round(sum(scores.values()) / len(scores), 2) if scores else None

        _ensure(all_models, cid, name=name)

        all_models[cid]["aliases"]["livebench"] = name
        all_models[cid]["benchmarks"]["livebench"] = {
            "average": overall,
            **cat_avgs,
            "tasks": scores,
        }

    # ── ARENA AI (TEXT) ──
    arena_text_path = os.path.join(SRC, "arena_text.json")
    with open(arena_text_path) as f:
        arena_text_data = json.load(f)

    for m in arena_text_data.get("models", []):
        aid = m["model"]
        cid = resolve_from_slug(aid)

        _ensure(all_models, cid, name=aid, creator=m.get("vendor"), model_type=m.get("license"))

        all_models[cid]["aliases"]["arena"] = aid
        all_models[cid]["creator"] = all_models[cid].get("creator") or m.get("vendor")
        all_models[cid]["benchmarks"]["arena_text"] = {
            "elo": m.get("score"),
            "ci": m.get("ci"),
            "votes": m.get("votes"),
        }

    # ── ARENA AI (CODE) ──
    arena_code_path = os.path.join(SRC, "arena_code.json")
    with open(arena_code_path) as f:
        arena_code_data = json.load(f)

    for m in arena_code_data.get("models", []):
        aid = m["model"]
        cid = resolve_from_slug(aid)

        _ensure(all_models, cid, name=aid, creator=m.get("vendor"), model_type=m.get("license"))

        all_models[cid]["aliases"]["arena_code"] = aid
        all_models[cid]["creator"] = all_models[cid].get("creator") or m.get("vendor")
        all_models[cid]["benchmarks"]["arena_code"] = {
            "elo": m.get("score"),
            "ci": m.get("ci"),
            "votes": m.get("votes"),
        }

    # ── OPENLLM v2 (AA subset) ──
    ollm_path = os.path.join(SRC, "openllm_aa_subset.json")
    with open(ollm_path) as f:
        ollm_models = json.load(f)

    for m in ollm_models:
        fullname = m.get("fullname", "")
        cid = openllm_name_to_canonical(fullname)
        if not cid:
            continue

        _ensure(all_models, cid, name=fullname)

        all_models[cid]["aliases"]["openllm"] = fullname
        all_models[cid]["benchmarks"]["openllm"] = {
            "average": m.get("Average ⬆️"),
            "ifeval": m.get("IFEval"),
            "bbh": m.get("BBH"),
            "math_lvl_5": m.get("MATH Lvl 5"),
            "gpqa": m.get("GPQA"),
            "musr": m.get("MUSR"),
            "mmlu_pro": m.get("MMLU-PRO"),
        }

        meta_updates = {}
        if m.get("#Params (B)") is not None:
            meta_updates["params_b"] = m.get("#Params (B)")
        if m.get("CO₂ cost (kg)") is not None:
            meta_updates["co2_kg"] = m.get("CO₂ cost (kg)")
        if m.get("Architecture"):
            meta_updates["architecture"] = m.get("Architecture")
        if m.get("Hub License"):
            meta_updates["license"] = m.get("Hub License")
        if m.get("Precision"):
            meta_updates["precision"] = m.get("Precision")

        if meta_updates:
            if not all_models[cid]["meta"]:
                all_models[cid]["meta"] = {}
            all_models[cid]["meta"].update(meta_updates)

    # ── OPENROUTER ──
    or_path = os.path.join(SRC, "openrouter_models.json")
    with open(or_path) as f:
        or_models = json.load(f)

    for m in or_models:
        rid = m["id"]
        cid = openrouter_id_to_canonical(rid)

        _ensure(all_models, cid, name=m.get("name", rid), creator=m.get("vendor"))

        all_models[cid]["aliases"]["openrouter"] = rid
        all_models[cid]["pricing"]["openrouter"] = {}

        def or_price(price_str):
            if price_str is None or price_str == "" or float(price_str) < 0:
                return None
            return float(price_str)

        inp = or_price(m.get("input_price"))
        out = or_price(m.get("output_price"))
        cache = or_price(m.get("cache_read_price"))
        cache_write = or_price(m.get("cache_write_price"))

        if inp is not None:
            all_models[cid]["pricing"]["openrouter"]["inp_price"] = inp  # $/token
            all_models[cid]["pricing"]["openrouter"]["inp_price_per_m"] = inp * 1_000_000  # $/Mtok
        if out is not None:
            all_models[cid]["pricing"]["openrouter"]["out_price"] = out
            all_models[cid]["pricing"]["openrouter"]["out_price_per_m"] = out * 1_000_000
        if cache is not None:
            all_models[cid]["pricing"]["openrouter"]["cache_read_price"] = cache
            all_models[cid]["pricing"]["openrouter"]["cache_read_price_per_m"] = cache * 1_000_000
        if cache_write is not None:
            all_models[cid]["pricing"]["openrouter"]["cache_write_price"] = cache_write
            all_models[cid]["pricing"]["openrouter"]["cache_write_price_per_m"] = cache_write * 1_000_000

        all_models[cid]["pricing"]["openrouter"]["vendor"] = m.get("vendor")

    resolve_or_context(all_models, or_models)

    misc_path = os.path.join(SRC, "misc.json")
    if os.path.exists(misc_path):
        with open(misc_path) as f:
            misc = json.load(f)
        for cid, record in misc.items():
            if cid not in all_models:
                continue
            meta = all_models[cid].setdefault("meta", {})
            for key, val in record.items():
                if key not in meta or meta[key] is None:
                    meta[key] = val

    # 3. BUILD NAME MAP
    name_map = {}
    for cid, model in all_models.items():
        for source, sid in model.get("aliases", {}).items():
            key = f"{source}:{sid}"
            name_map[key] = cid

    # 4. WRITE OUTPUT
    output_models = []
    for cid in sorted(all_models.keys()):
        model = all_models[cid]
        if "livebench" in model.get("benchmarks", {}):
            lb = model["benchmarks"]["livebench"]
            if "tasks" in lb:
                del lb["tasks"]
        output_models.append(model)

    output = {
        "meta": {
            "generated": today,
            "version": "1.0",
            "model_count": len(output_models),
            "source_count": {
                "aa": len(aa_models),
                "livebench": len(lb_models),
                "arena_text": len(arena_text_data.get("models", [])),
                "arena_code": len(arena_code_data.get("models", [])),
                "openllm_aa_subset": len(ollm_models),
                "openrouter": len(or_models),
            },
            "sources": ["AA", "LiveBench", "Arena Text", "Arena Code", "OpenLLM v2", "OpenRouter", "Cost Breakdown"],
            "name_map_size": len(name_map),
        },
        "name_map": name_map,
        "models": [RegistryModel.from_flat(m).to_dict() for m in output_models],
    }

    with open(OUT, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Written {len(output_models)} models to {OUT}")
    print(f"Name map: {len(name_map)} alias entries")
    print(f"Model registry size: {len(json.dumps(output)):,} bytes")

    # ── Summary ──
    print("\n── SOURCE COVERAGE ──")
    source_count = {"aa": 0, "livebench": 0, "arena": 0, "openllm": 0, "openrouter": 0}
    multi_source = 0
    for m in output_models:
        has_p = [s for s in m.get("pricing", {}) if m["pricing"][s]]
        has_b = [s for s in m.get("benchmarks", {}) if m["benchmarks"][s]]
        total = len(set(has_p + has_b))
        if total >= 2:
            multi_source += 1
        for s in has_b:
            source_count[s] = source_count.get(s, 0) + 1
        for s in has_p:
            if s not in source_count:
                source_count[s] = 0
            source_count[s] += 1

    for s, c in sorted(source_count.items()):
        print(f"  {s:15s} {c} models")
    print(f"\n  Models with 2+ sources: {multi_source}")

    aa_plus = 0
    for m in output_models:
        if "aa" in m.get("benchmarks", {}) and len([s for s in m.get("benchmarks", {}) if s != "aa"]) > 0:
            aa_plus += 1
        if "aa" in m.get("pricing", {}) and "openrouter" in m.get("pricing", {}):
            aa_plus += 1
    print(f"  AA models with cross-source data: {aa_plus}")

    print("\n── TOP 20 MODELS (by sources) ──")
    def source_count_for_model(m):
        return len([s for s in m.get("pricing", {}) if m["pricing"][s]]) + len([s for s in m.get("benchmarks", {}) if m["benchmarks"][s]])

    sorted_by_sources = sorted(output_models, key=source_count_for_model, reverse=True)
    for m in sorted_by_sources[:20]:
        p = [s for s in m.get("pricing", {}) if m["pricing"][s]]
        b = [s for s in m.get("benchmarks", {}) if m["benchmarks"][s]]
        print(f"  {m['id']:40s} P:{','.join(p):25s} B:{','.join(b)}")

    return {"model_count": len(output_models), "name_map_size": len(name_map)}

if __name__ == "__main__":
    run()
