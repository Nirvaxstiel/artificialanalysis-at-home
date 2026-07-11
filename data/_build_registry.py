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
from _result import ok, err


BASE = None


def _load_json(path: str):
    try:
        with open(path) as f:
            return ok(json.load(f))
    except (OSError, json.JSONDecodeError) as e:  # noqa: BLE001
        return err(f"{os.path.basename(path)}: {e}")


def _load_csv(path: str):
    try:
        with open(path, newline="") as f:
            return ok(list(csv.DictReader(f)))
    except (OSError, csv.Error) as e:  # noqa: BLE001
        return err(f"{os.path.basename(path)}: {e}")

def _ensure(all_models, cid, **overrides):
    if cid not in all_models:
        all_models[cid] = {"id": cid, "name": None, "creator": None,
                           "model_type": None,
                           "meta": {}, "pricing": {},
                           "benchmarks": {}, "aliases": {},
                           **overrides}
    return all_models[cid]


def step_aa(s):
    r = get_aa_models(BASE)
    if r.is_err():
        return err(f"aa build: {r.error}")
    models = r.unwrap()
    s["all_models"].update(models)
    s["counts"]["aa"] = len(models)
    return ok(s)


def step_aa_img(s):
    for cid, img in get_aa_img_models(BASE).items():
        m = s["all_models"].setdefault(cid, {
            "id": cid, "name": None, "creator": None, "model_type": None,
            "meta": {}, "pricing": {}, "benchmarks": {}, "aliases": {}})
        img_b = img.get("benchmarks", {}).get("aa_img")
        if img_b:
            m.setdefault("benchmarks", {}).setdefault("aa_img", {}).update(img_b)
        img_p = img.get("pricing", {}).get("aa")
        if img_p:
            ep = m.setdefault("pricing", {}).setdefault("aa", {})
            for k, v in img_p.items():
                if v is not None and ep.get(k) is None:
                    ep[k] = v
        img_meta = img.get("meta", {})
        if img_meta:
            m.setdefault("meta", {}).update(img_meta)
    return ok(s)


def step_scrape_progress(s):
    scrape_path = os.path.join(s["src"], "aa", "aa_scrape_progress.json")
    scraped_slugs = set()
    if os.path.exists(scrape_path):
        try:
            with open(scrape_path) as f:
                sp = json.load(f)
            scraped_slugs = set(sp.get("scraped", []))
        except (OSError, ValueError):
            pass
    for cid in get_aa_img_models(BASE):
        if cid in scraped_slugs:
            s["all_models"].setdefault(cid, {}).setdefault("meta", {})["aa_img_scraped"] = True
    return ok(s)


def step_dirac(s):
    for cid, d in get_dirac_models(BASE).items():
        m = s["all_models"].setdefault(cid, {
            "id": cid, "name": None, "creator": None, "model_type": None,
            "meta": {}, "pricing": {}, "benchmarks": {}, "aliases": {}})
        db = d.get("benchmarks", {}).get("dirac")
        if db:
            m.setdefault("benchmarks", {}).setdefault("dirac", {}).update(db)
        dmeta = d.get("meta", {})
        if dmeta:
            m.setdefault("meta", {}).update(dmeta)
    return ok(s)


def step_livebench(s):
    cat = _load_json(os.path.join(s["src"], "livebench_categories_2026_01_08.json"))
    if cat.is_err():
        return err(cat.error)
    lb_categories = cat.unwrap()
    task_to_cat = {t: cn for cn, tasks in lb_categories.items() for t in tasks}
    lb = _load_csv(os.path.join(s["src"], "livebench_2026_01_08.csv"))
    if lb.is_err():
        return err(lb.error)
    for m in lb.unwrap():
        name = m["model"]
        cid = livebench_name_to_canonical(name)
        scores, cat_scores = {}, {}
        for task, val in m.items():
            if task == "model" or val == "" or val is None:
                continue
            try:
                v = float(val)
            except (ValueError, TypeError):
                continue
            scores[task] = v
            cat = task_to_cat.get(task, "Other")
            cat_scores.setdefault(cat, []).append(v)
        cat_avgs = {c: round(sum(vs) / len(vs), 2) for c, vs in cat_scores.items()}
        overall = round(sum(scores.values()) / len(scores), 2) if scores else None
        _ensure(s["all_models"], cid, name=name)
        s["all_models"][cid]["aliases"]["livebench"] = name
        s["all_models"][cid]["benchmarks"]["livebench"] = {
            "average": overall, **cat_avgs, "tasks": scores}
    s["counts"]["livebench"] = len(lb.unwrap())
    return ok(s)


def step_arena_text(s):
    r = _load_json(os.path.join(s["src"], "arena_text.json"))
    if r.is_err():
        return err(r.error)
    for m in r.unwrap().get("models", []):
        aid = m["model"]
        cid = resolve_from_slug(aid)
        _ensure(s["all_models"], cid, name=aid, creator=m.get("vendor"), model_type=m.get("license"))
        s["all_models"][cid]["aliases"]["arena"] = aid
        s["all_models"][cid]["creator"] = s["all_models"][cid].get("creator") or m.get("vendor")
        s["all_models"][cid]["benchmarks"]["arena_text"] = {
            "elo": m.get("score"), "ci": m.get("ci"), "votes": m.get("votes")}
    s["counts"]["arena_text"] = len(r.unwrap().get("models", []))
    return ok(s)


def step_arena_code(s):
    r = _load_json(os.path.join(s["src"], "arena_code.json"))
    if r.is_err():
        return err(r.error)
    for m in r.unwrap().get("models", []):
        aid = m["model"]
        cid = resolve_from_slug(aid)
        _ensure(s["all_models"], cid, name=aid, creator=m.get("vendor"), model_type=m.get("license"))
        s["all_models"][cid]["aliases"]["arena_code"] = aid
        s["all_models"][cid]["creator"] = s["all_models"][cid].get("creator") or m.get("vendor")
        s["all_models"][cid]["benchmarks"]["arena_code"] = {
            "elo": m.get("score"), "ci": m.get("ci"), "votes": m.get("votes")}
    s["counts"]["arena_code"] = len(r.unwrap().get("models", []))
    return ok(s)


def step_openllm(s):
    r = _load_json(os.path.join(s["src"], "openllm_aa_subset.json"))
    if r.is_err():
        return err(r.error)
    for m in r.unwrap():
        cid = openllm_name_to_canonical(m.get("fullname", "")).unwrap_or(None)
        if not cid:
            continue
        _ensure(s["all_models"], cid, name=m.get("fullname"))
        s["all_models"][cid]["aliases"]["openllm"] = m.get("fullname")
        s["all_models"][cid]["benchmarks"]["openllm"] = {
            "average": m.get("Average ⬆️"), "ifeval": m.get("IFEval"), "bbh": m.get("BBH"),
            "math_lvl_5": m.get("MATH Lvl 5"), "gpqa": m.get("GPQA"),
            "musr": m.get("MUSR"), "mmlu_pro": m.get("MMLU-PRO")}
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
            s["all_models"][cid].setdefault("meta", {}).update(meta_updates)
    s["counts"]["openllm_aa_subset"] = len(r.unwrap())
    return ok(s)


def step_openrouter(s):
    r = _load_json(os.path.join(s["src"], "openrouter_models.json"))
    if r.is_err():
        return err(r.error)
    or_models = r.unwrap()

    def or_price(price_str):
        if price_str is None or price_str == "" or float(price_str) < 0:
            return None
        return float(price_str)

    for m in or_models:
        rid = m["id"]
        cid = openrouter_id_to_canonical(rid)
        _ensure(s["all_models"], cid, name=m.get("name", rid), creator=m.get("vendor"))
        s["all_models"][cid]["aliases"]["openrouter"] = rid
        s["all_models"][cid]["pricing"]["openrouter"] = {}
        inp = or_price(m.get("input_price"))
        out = or_price(m.get("output_price"))
        cache = or_price(m.get("cache_read_price"))
        cache_write = or_price(m.get("cache_write_price"))
        if inp is not None:
            s["all_models"][cid]["pricing"]["openrouter"]["inp_price"] = inp
            s["all_models"][cid]["pricing"]["openrouter"]["inp_price_per_m"] = inp * 1_000_000
        if out is not None:
            s["all_models"][cid]["pricing"]["openrouter"]["out_price"] = out
            s["all_models"][cid]["pricing"]["openrouter"]["out_price_per_m"] = out * 1_000_000
        if cache is not None:
            s["all_models"][cid]["pricing"]["openrouter"]["cache_read_price"] = cache
            s["all_models"][cid]["pricing"]["openrouter"]["cache_read_price_per_m"] = cache * 1_000_000
        if cache_write is not None:
            s["all_models"][cid]["pricing"]["openrouter"]["cache_write_price"] = cache_write
            s["all_models"][cid]["pricing"]["openrouter"]["cache_write_price_per_m"] = cache_write * 1_000_000
        s["all_models"][cid]["pricing"]["openrouter"]["vendor"] = m.get("vendor")
    s["counts"]["openrouter"] = len(or_models)
    resolve_or_context(s["all_models"], or_models)
    return ok(s)


def step_misc(s):
    misc_path = os.path.join(s["src"], "misc.json")
    if os.path.exists(misc_path):
        try:
            with open(misc_path) as f:
                misc = json.load(f)
        except (OSError, ValueError):
            return ok(s)
        for cid, record in misc.items():
            if cid not in s["all_models"]:
                continue
            meta = s["all_models"][cid].setdefault("meta", {})
            for key, val in record.items():
                if key not in meta or meta[key] is None:
                    meta[key] = val
    return ok(s)


def step_name_map(s):
    name_map = {}
    for cid, model in s["all_models"].items():
        for source, sid in model.get("aliases", {}).items():
            name_map[f"{source}:{sid}"] = cid
    s["name_map"] = name_map
    return ok(s)


def step_write(s):
    output_models = []
    for cid in sorted(s["all_models"].keys()):
        model = s["all_models"][cid]
        if "livebench" in model.get("benchmarks", {}):
            lb = model["benchmarks"]["livebench"]
            if "tasks" in lb:
                del lb["tasks"]
        output_models.append(model)
    output = {
        "meta": {
            "generated": s["today"],
            "version": "1.0",
            "model_count": len(output_models),
            "source_count": s["counts"],
            "sources": ["AA", "LiveBench", "Arena Text", "Arena Code", "OpenLLM v2", "OpenRouter", "Cost Breakdown"],
            "name_map_size": len(s["name_map"]),
        },
        "name_map": s["name_map"],
        "models": [RegistryModel.from_flat(m).to_dict() for m in output_models],
    }
    try:
        with open(s["out"], "w") as f:
            json.dump(output, f, indent=2)
    except OSError as e:  # noqa: BLE001
        return err(f"{os.path.basename(s['out'])}: {e}")
    print(f"Written {len(output_models)} models to {s['out']}")
    print(f"Name map: {len(s['name_map'])} alias entries")
    print(f"Model registry size: {len(json.dumps(output)):,} bytes")
    s["output_models"] = output_models
    return ok(s)


def run(ctx=None):
    global BASE
    if ctx and ctx.get("root"):
        BASE = Path(ctx["root"])
    else:
        BASE = Path(__file__).resolve().parent.parent

    SRC = os.path.join(BASE, "data", "sources")
    OUT = os.path.join(BASE, "data", "model_registry.json")

    state = {
        "all_models": {},
        "src": SRC,
        "out": OUT,
        "today": date.today().isoformat(),
        "counts": {},
    }

    s = state
    for step in (step_aa, step_aa_img, step_scrape_progress, step_dirac,
                 step_livebench, step_arena_text, step_arena_code,
                 step_openllm, step_openrouter, step_misc,
                 step_name_map, step_write):
        r = step(s)
        if r.is_err():
            return err(r.error)
        s = r.unwrap()

    output_models = s["output_models"]

    # ── Summary ──
    print("\n── SOURCE COVERAGE ──")
    source_count = {"aa": 0, "livebench": 0, "arena": 0, "openllm": 0, "openrouter": 0}
    multi_source = 0
    for m in output_models:
        has_p = [s_ for s_ in m.get("pricing", {}) if m["pricing"][s_]]
        has_b = [s_ for s_ in m.get("benchmarks", {}) if m["benchmarks"][s_]]
        total = len(set(has_p + has_b))
        if total >= 2:
            multi_source += 1
        for s_ in has_b:
            source_count[s_] = source_count.get(s_, 0) + 1
        for s_ in has_p:
            if s_ not in source_count:
                source_count[s_] = 0
            source_count[s_] += 1
    for s_, c in sorted(source_count.items()):
        print(f"  {s_:15s} {c} models")
    print(f"\n  Models with 2+ sources: {multi_source}")
    aa_plus = 0
    for m in output_models:
        if "aa" in m.get("benchmarks", {}) and len([s_ for s_ in m.get("benchmarks", {}) if s_ != "aa"]) > 0:
            aa_plus += 1
        if "aa" in m.get("pricing", {}) and "openrouter" in m.get("pricing", {}):
            aa_plus += 1
    print(f"  AA models with cross-source data: {aa_plus}")
    print("\n── TOP 20 MODELS (by sources) ──")
    def source_count_for_model(m):
        return len([s_ for s_ in m.get("pricing", {}) if m["pricing"][s_]]) + len([s_ for s_ in m.get("benchmarks", {}) if m["benchmarks"][s_]])
    sorted_by_sources = sorted(output_models, key=source_count_for_model, reverse=True)
    for m in sorted_by_sources[:20]:
        p = [s_ for s_ in m.get("pricing", {}) if m["pricing"][s_]]
        b = [s_ for s_ in m.get("benchmarks", {}) if m["benchmarks"][s_]]
        print(f"  {m['id']:40s} P:{','.join(p):25s} B:{','.join(b)}")
    return ok({"model_count": len(output_models), "name_map_size": len(s["name_map"])})

if __name__ == "__main__":
    result = run()
    if result.is_err():
        print("REGISTRY BUILD FAILED:", result.error)
        raise SystemExit(1)
