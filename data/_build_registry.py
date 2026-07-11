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


def step_aa(state):
    result = get_aa_models(BASE)
    if result.is_err():
        return err(f"aa build: {result.error}")
    models = result.unwrap()
    state["all_models"].update(models)
    state["counts"]["aa"] = len(models)
    return ok(state)


def step_aa_img(state):
    for canonical_id, img in get_aa_img_models(BASE).items():
        model = state["all_models"].setdefault(canonical_id, {
            "id": canonical_id, "name": None, "creator": None, "model_type": None,
            "meta": {}, "pricing": {}, "benchmarks": {}, "aliases": {}})
        img_benchmarks = img.get("benchmarks", {}).get("aa_img")
        if img_benchmarks:
            model.setdefault("benchmarks", {}).setdefault("aa_img", {}).update(img_benchmarks)
        img_pricing = img.get("pricing", {}).get("aa")
        if img_pricing:
            pricing_entry = model.setdefault("pricing", {}).setdefault("aa", {})
            for key, value in img_pricing.items():
                if value is not None and pricing_entry.get(key) is None:
                    pricing_entry[key] = value
        img_meta = img.get("meta", {})
        if img_meta:
            model.setdefault("meta", {}).update(img_meta)
    return ok(state)


def step_scrape_progress(state):
    scrape_path = os.path.join(state["src"], "aa", "aa_scrape_progress.json")
    scraped_slugs = set()
    if os.path.exists(scrape_path):
        try:
            with open(scrape_path) as f:
                scrape_progress = json.load(f)
            scraped_slugs = set(scrape_progress.get("scraped", []))
        except (OSError, ValueError):
            pass
    for canonical_id in get_aa_img_models(BASE):
        if canonical_id in scraped_slugs:
            state["all_models"].setdefault(canonical_id, {}).setdefault("meta", {})["aa_img_scraped"] = True
    return ok(state)


def step_dirac(state):
    for canonical_id, record in get_dirac_models(BASE).items():
        model = state["all_models"].setdefault(canonical_id, {
            "id": canonical_id, "name": None, "creator": None, "model_type": None,
            "meta": {}, "pricing": {}, "benchmarks": {}, "aliases": {}})
        dirac_benchmarks = record.get("benchmarks", {}).get("dirac")
        if dirac_benchmarks:
            model.setdefault("benchmarks", {}).setdefault("dirac", {}).update(dirac_benchmarks)
        dirac_meta = record.get("meta", {})
        if dirac_meta:
            model.setdefault("meta", {}).update(dirac_meta)
    return ok(state)


def step_livebench(state):
    categories_result = _load_json(os.path.join(state["src"], "livebench_categories_2026_01_08.json"))
    if categories_result.is_err():
        return err(categories_result.error)
    category_map = categories_result.unwrap()
    task_to_category = {task: cat for cat, tasks in category_map.items() for task in tasks}
    rows_result = _load_csv(os.path.join(state["src"], "livebench_2026_01_08.csv"))
    if rows_result.is_err():
        return err(rows_result.error)
    livebench_rows = rows_result.unwrap()
    for row in livebench_rows:
        model_name = row["model"]
        canonical_id = livebench_name_to_canonical(model_name)
        task_scores, category_scores = {}, {}
        for task_name, value in row.items():
            if task_name == "model" or value == "" or value is None:
                continue
            try:
                numeric = float(value)
            except (ValueError, TypeError):
                continue
            task_scores[task_name] = numeric
            category = task_to_category.get(task_name, "Other")
            category_scores.setdefault(category, []).append(numeric)
        category_averages = {cat: round(sum(vals) / len(vals), 2) for cat, vals in category_scores.items()}
        overall = round(sum(task_scores.values()) / len(task_scores), 2) if task_scores else None
        _ensure(state["all_models"], canonical_id, name=model_name)
        state["all_models"][canonical_id]["aliases"]["livebench"] = model_name
        state["all_models"][canonical_id]["benchmarks"]["livebench"] = {
            "average": overall, **category_averages, "tasks": task_scores}
    state["counts"]["livebench"] = len(livebench_rows)
    return ok(state)


def step_arena_text(state):
    result = _load_json(os.path.join(state["src"], "arena_text.json"))
    if result.is_err():
        return err(result.error)
    for model in result.unwrap().get("models", []):
        arena_id = model["model"]
        canonical_id = resolve_from_slug(arena_id)
        _ensure(state["all_models"], canonical_id, name=arena_id,
                creator=model.get("vendor"), model_type=model.get("license"))
        state["all_models"][canonical_id]["aliases"]["arena"] = arena_id
        state["all_models"][canonical_id]["creator"] = \
            state["all_models"][canonical_id].get("creator") or model.get("vendor")
        state["all_models"][canonical_id]["benchmarks"]["arena_text"] = {
            "elo": model.get("score"), "ci": model.get("ci"), "votes": model.get("votes")}
    state["counts"]["arena_text"] = len(result.unwrap().get("models", []))
    return ok(state)


def step_arena_code(state):
    result = _load_json(os.path.join(state["src"], "arena_code.json"))
    if result.is_err():
        return err(result.error)
    for model in result.unwrap().get("models", []):
        arena_id = model["model"]
        canonical_id = resolve_from_slug(arena_id)
        _ensure(state["all_models"], canonical_id, name=arena_id,
                creator=model.get("vendor"), model_type=model.get("license"))
        state["all_models"][canonical_id]["aliases"]["arena_code"] = arena_id
        state["all_models"][canonical_id]["creator"] = \
            state["all_models"][canonical_id].get("creator") or model.get("vendor")
        state["all_models"][canonical_id]["benchmarks"]["arena_code"] = {
            "elo": model.get("score"), "ci": model.get("ci"), "votes": model.get("votes")}
    state["counts"]["arena_code"] = len(result.unwrap().get("models", []))
    return ok(state)


def step_openllm(state):
    result = _load_json(os.path.join(state["src"], "openllm_aa_subset.json"))
    if result.is_err():
        return err(result.error)
    for model in result.unwrap():
        canonical_id = openllm_name_to_canonical(model.get("fullname", "")).unwrap_or(None)
        if not canonical_id:
            continue
        _ensure(state["all_models"], canonical_id, name=model.get("fullname"))
        state["all_models"][canonical_id]["aliases"]["openllm"] = model.get("fullname")
        state["all_models"][canonical_id]["benchmarks"]["openllm"] = {
            "average": model.get("Average ⬆️"), "ifeval": model.get("IFEval"), "bbh": model.get("BBH"),
            "math_lvl_5": model.get("MATH Lvl 5"), "gpqa": model.get("GPQA"),
            "musr": model.get("MUSR"), "mmlu_pro": model.get("MMLU-PRO")}
        meta_updates = {}
        if model.get("#Params (B)") is not None:
            meta_updates["params_b"] = model.get("#Params (B)")
        if model.get("CO₂ cost (kg)") is not None:
            meta_updates["co2_kg"] = model.get("CO₂ cost (kg)")
        if model.get("Architecture"):
            meta_updates["architecture"] = model.get("Architecture")
        if model.get("Hub License"):
            meta_updates["license"] = model.get("Hub License")
        if model.get("Precision"):
            meta_updates["precision"] = model.get("Precision")
        if meta_updates:
            state["all_models"][canonical_id].setdefault("meta", {}).update(meta_updates)
    state["counts"]["openllm_aa_subset"] = len(result.unwrap())
    return ok(state)


def step_openrouter(state):
    result = _load_json(os.path.join(state["src"], "openrouter_models.json"))
    if result.is_err():
        return err(result.error)
    openrouter_models = result.unwrap()

    def parse_price(price_str):
        if price_str is None or price_str == "" or float(price_str) < 0:
            return None
        return float(price_str)

    for model in openrouter_models:
        openrouter_id = model["id"]
        canonical_id = openrouter_id_to_canonical(openrouter_id)
        _ensure(state["all_models"], canonical_id, name=model.get("name", openrouter_id), creator=model.get("vendor"))
        state["all_models"][canonical_id]["aliases"]["openrouter"] = openrouter_id
        state["all_models"][canonical_id]["pricing"]["openrouter"] = {}
        input_price = parse_price(model.get("input_price"))
        output_price = parse_price(model.get("output_price"))
        cache_read_price = parse_price(model.get("cache_read_price"))
        cache_write_price = parse_price(model.get("cache_write_price"))
        if input_price is not None:
            state["all_models"][canonical_id]["pricing"]["openrouter"]["inp_price"] = input_price
            state["all_models"][canonical_id]["pricing"]["openrouter"]["inp_price_per_m"] = input_price * 1_000_000
        if output_price is not None:
            state["all_models"][canonical_id]["pricing"]["openrouter"]["out_price"] = output_price
            state["all_models"][canonical_id]["pricing"]["openrouter"]["out_price_per_m"] = output_price * 1_000_000
        if cache_read_price is not None:
            state["all_models"][canonical_id]["pricing"]["openrouter"]["cache_read_price"] = cache_read_price
            state["all_models"][canonical_id]["pricing"]["openrouter"]["cache_read_price_per_m"] = cache_read_price * 1_000_000
        if cache_write_price is not None:
            state["all_models"][canonical_id]["pricing"]["openrouter"]["cache_write_price"] = cache_write_price
            state["all_models"][canonical_id]["pricing"]["openrouter"]["cache_write_price_per_m"] = cache_write_price * 1_000_000
        state["all_models"][canonical_id]["pricing"]["openrouter"]["vendor"] = model.get("vendor")
    state["counts"]["openrouter"] = len(openrouter_models)
    resolve_or_context(state["all_models"], openrouter_models)
    return ok(state)


def step_misc(state):
    misc_path = os.path.join(state["src"], "misc.json")
    if os.path.exists(misc_path):
        try:
            with open(misc_path) as f:
                misc = json.load(f)
        except (OSError, ValueError):
            return ok(state)
        for canonical_id, record in misc.items():
            if canonical_id not in state["all_models"]:
                continue
            meta = state["all_models"][canonical_id].setdefault("meta", {})
            for key, value in record.items():
                if key not in meta or meta[key] is None:
                    meta[key] = value
    return ok(state)


def step_name_map(state):
    name_map = {}
    for canonical_id, model in state["all_models"].items():
        for source, source_id in model.get("aliases", {}).items():
            name_map[f"{source}:{source_id}"] = canonical_id
    state["name_map"] = name_map
    return ok(state)


def step_write(state):
    output_models = []
    for canonical_id in sorted(state["all_models"].keys()):
        model = state["all_models"][canonical_id]
        if "livebench" in model.get("benchmarks", {}):
            livebench = model["benchmarks"]["livebench"]
            if "tasks" in livebench:
                del livebench["tasks"]
        output_models.append(model)
    output = {
        "meta": {
            "generated": state["today"],
            "version": "1.0",
            "model_count": len(output_models),
            "source_count": state["counts"],
            "sources": ["AA", "LiveBench", "Arena Text", "Arena Code", "OpenLLM v2", "OpenRouter", "Cost Breakdown"],
            "name_map_size": len(state["name_map"]),
        },
        "name_map": state["name_map"],
        "models": [RegistryModel.from_flat(m).to_dict() for m in output_models],
    }
    try:
        with open(state["out"], "w") as f:
            json.dump(output, f, indent=2)
    except OSError as e:  # noqa: BLE001
        return err(f"{os.path.basename(state['out'])}: {e}")
    print(f"Written {len(output_models)} models to {state['out']}")
    print(f"Name map: {len(state['name_map'])} alias entries")
    print(f"Model registry size: {len(json.dumps(output)):,} bytes")
    state["output_models"] = output_models
    return ok(state)


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

    current_state = state
    for step in (step_aa, step_aa_img, step_scrape_progress, step_dirac,
                 step_livebench, step_arena_text, step_arena_code,
                 step_openllm, step_openrouter, step_misc,
                 step_name_map, step_write):
        result = step(current_state)
        if result.is_err():
            return err(result.error)
        current_state = result.unwrap()

    output_models = current_state["output_models"]

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
    return ok({"model_count": len(output_models), "name_map_size": len(current_state["name_map"])})

if __name__ == "__main__":
    result = run()
    if result.is_err():
        print("REGISTRY BUILD FAILED:", result.error)
        raise SystemExit(1)
