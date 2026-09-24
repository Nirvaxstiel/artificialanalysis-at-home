import json, csv, os, re
from datetime import date
from pathlib import Path

from .sources.aa._build import get_aa_models
from .sources.dirac._build import get_dirac_models
from ._canonical import (
    resolve_from_slug, livebench_name_to_canonical,
    openrouter_id_to_canonical, openllm_name_to_canonical,
    costbd_name_to_canonical,
    canonical_to_or_id, resolve_or_context,
    normalize_creator,
)
from ._domain._entities import RegistryModel
from _result import ok, err
from _pipeline import Pipeline


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
    if not cid or cid not in all_models:
        return None
    model = all_models[cid]
    for key, value in overrides.items():
        fallback_name = model.get("aliases", {}).get("aa")
        if value is not None and (
            model.get(key) is None or (key == "name" and model.get(key) == fallback_name)
        ):
            model[key] = value
    return model


def step_aa(state):
    result = get_aa_models(BASE)
    if result.is_err():
        return err(f"aa build: {result.error}")
    models = result.unwrap()
    state["all_models"].update(models)
    state["counts"]["aa"] = len(models)
    return ok(state)


def _normalize_id(model_id: str) -> str:
    return model_id.replace(".", "").replace("-", "").replace("_", "").lower()


SOURCE_NAMES = {
    "aa": "AA",
    "dirac": "Dirac.run",
    "livebench": "LiveBench",
    "arena_code": "Arena Code",
    "arena_text": "Arena Text",
    "openllm_aa_subset": "OpenLLM v2",
    "openrouter": "OpenRouter",
}

UNDATED_SNAPSHOTS = {
    "aa": "2026-09-24",
    "dirac": "2026-07-23",
    "openllm_aa_subset": "2026-07-04",
}

SOURCE_NOTES = {
    "aa": "Charts and JSON-LD captured 2026-09-10; live API and public model catalog refreshed 2026-09-24.",
    "dirac": "Observed prefix-cache hit rates per model (max across providers), sourced from dirac.run full table via OpenRouter Effective Pricing.",
}


def _snapshot_date_from_file(src, filename, *path):
    result = _load_json(os.path.join(src, filename))
    if result.is_err():
        return None
    node = result.unwrap()
    for key in path:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return (node or "")[:10] or None


def _livebench_snapshot_date(src):
    match = re.search(r"livebench_(\d{4})_(\d{2})_(\d{2})", " ".join(os.listdir(src)))
    return "-".join(match.groups()) if match else None


def _source_meta(state):
    as_of = {
        **UNDATED_SNAPSHOTS,
        "arena_code": _snapshot_date_from_file(state["src"], "arena_code.json", "meta", "fetched_at"),
        "arena_text": _snapshot_date_from_file(state["src"], "arena_text.json", "meta", "fetched_at"),
        "livebench": _livebench_snapshot_date(state["src"]),
    }
    meta = {}
    for source_id, name in SOURCE_NAMES.items():
        entry = {"models": state["counts"].get(source_id, 0), "as_of": as_of.get(source_id)}
        if source_id in SOURCE_NOTES:
            entry["note"] = SOURCE_NOTES[source_id]
        meta[name] = entry
    return meta


def _resolve_existing(all_models: dict, canonical_id: str) -> str | None:
    if canonical_id in all_models and all_models[canonical_id].get("name"):
        return canonical_id
    normalized = _normalize_id(canonical_id)
    candidates = [cid for cid in all_models
                  if _normalize_id(cid) == normalized and all_models[cid].get("name")]
    return candidates[0] if len(candidates) == 1 else None


def step_dirac(state):
    all_models = state["all_models"]
    attached = 0
    unresolved = []
    for canonical_id, record in get_dirac_models(BASE).items():
        target = _resolve_existing(all_models, canonical_id)
        if target is None:
            unresolved.append(canonical_id)
            continue
        model = all_models[target]
        dirac_benchmarks = record.get("benchmarks", {}).get("dirac")
        if dirac_benchmarks:
            model.setdefault("benchmarks", {}).setdefault("dirac", {}).update(dirac_benchmarks)
        dirac_meta = record.get("meta", {})
        if dirac_meta:
            model.setdefault("meta", {}).update(dirac_meta)
        attached += 1
    state["counts"]["dirac"] = attached
    state["dirac_unresolved"] = unresolved
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
    attached = 0
    for row in livebench_rows:
        model_name = row["model"]
        canonical_id = livebench_name_to_canonical(model_name)
        model = _ensure(state["all_models"], canonical_id, name=model_name)
        if model is None:
            continue
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
        model.setdefault("aliases", {})["livebench"] = model_name
        model.setdefault("benchmarks", {})["livebench"] = {
            "average": overall, **category_averages, "tasks": task_scores}
        attached += 1
    state["counts"]["livebench"] = attached
    return ok(state)


def step_arena_text(state):
    result = _load_json(os.path.join(state["src"], "arena_text.json"))
    if result.is_err():
        return err(result.error)
    attached = 0
    for model in result.unwrap().get("models", []):
        arena_id = model["model"]
        canonical_id = resolve_from_slug(arena_id)
        target = _ensure(state["all_models"], canonical_id, name=arena_id,
                         creator=normalize_creator(model.get("vendor")),
                         model_type=model.get("license"))
        if target is None:
            continue
        target.setdefault("aliases", {})["arena"] = arena_id
        target["creator"] = target.get("creator") or normalize_creator(model.get("vendor"))
        target.setdefault("benchmarks", {})["arena_text"] = {
            "elo": model.get("score"), "ci": model.get("ci"), "votes": model.get("votes")}
        attached += 1
    state["counts"]["arena_text"] = attached
    return ok(state)


def step_arena_code(state):
    result = _load_json(os.path.join(state["src"], "arena_code.json"))
    if result.is_err():
        return err(result.error)
    attached = 0
    for model in result.unwrap().get("models", []):
        arena_id = model["model"]
        canonical_id = resolve_from_slug(arena_id)
        target = _ensure(state["all_models"], canonical_id, name=arena_id,
                         creator=normalize_creator(model.get("vendor")),
                         model_type=model.get("license"))
        if target is None:
            continue
        target.setdefault("aliases", {})["arena_code"] = arena_id
        target["creator"] = target.get("creator") or normalize_creator(model.get("vendor"))
        target.setdefault("benchmarks", {})["arena_code"] = {
            "elo": model.get("score"), "ci": model.get("ci"), "votes": model.get("votes")}
        attached += 1
    state["counts"]["arena_code"] = attached
    return ok(state)


def step_openllm(state):
    result = _load_json(os.path.join(state["src"], "openllm_aa_subset.json"))
    if result.is_err():
        return err(result.error)
    attached = set()
    for model in result.unwrap():
        canonical_id = openllm_name_to_canonical(model.get("fullname", "")).unwrap_or(None)
        if not canonical_id:
            continue
        target = _ensure(state["all_models"], canonical_id, name=model.get("fullname"))
        if target is None:
            continue
        target.setdefault("aliases", {})["openllm"] = model.get("fullname")
        target.setdefault("benchmarks", {})["openllm"] = {
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
            target.setdefault("meta", {}).update(meta_updates)
        attached.add(canonical_id)
    state["counts"]["openllm_aa_subset"] = len(attached)
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

    attached = set()
    for model in openrouter_models:
        openrouter_id = model["id"]
        canonical_id = openrouter_id_to_canonical(openrouter_id)
        target = _ensure(state["all_models"], canonical_id,
                         name=model.get("name", openrouter_id),
                         creator=normalize_creator(model.get("vendor")))
        if target is None:
            continue
        target.setdefault("aliases", {})["openrouter"] = openrouter_id
        target.setdefault("pricing", {}).setdefault("openrouter", {})
        input_price = parse_price(model.get("input_price"))
        output_price = parse_price(model.get("output_price"))
        cache_read_price = parse_price(model.get("cache_read_price"))
        cache_write_price = parse_price(model.get("cache_write_price"))
        if input_price is not None:
            target["pricing"]["openrouter"]["inp_price"] = input_price
            target["pricing"]["openrouter"]["inp_price_per_m"] = input_price * 1_000_000
        if output_price is not None:
            target["pricing"]["openrouter"]["out_price"] = output_price
            target["pricing"]["openrouter"]["out_price_per_m"] = output_price * 1_000_000
        if cache_read_price is not None:
            target["pricing"]["openrouter"]["cache_read_price"] = cache_read_price
            target["pricing"]["openrouter"]["cache_read_price_per_m"] = cache_read_price * 1_000_000
        if cache_write_price is not None:
            target["pricing"]["openrouter"]["cache_write_price"] = cache_write_price
            target["pricing"]["openrouter"]["cache_write_price_per_m"] = cache_write_price * 1_000_000
        target["pricing"]["openrouter"]["vendor"] = model.get("vendor")
        attached.add(canonical_id)
    state["counts"]["openrouter"] = len(attached)
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
    # Central blended derive: any AA pricing with inp/out but no blended must
    # get it (AA "3-to-1" = (input + 3·output)/4), regardless of which source
    # (chart / enriched / scraped) supplied the prices. The per-source derives
    # only cover 2 of 3 paths, so scraped-only models (e.g. deepseek-v4-flash-high)
    # could land without blended.
    for model in state["all_models"].values():
        p = model.get("pricing", {}).get("aa")
        if p is not None and p.get("blended") is None \
                and p.get("inp_price") is not None and p.get("out_price") is not None:
            p["blended"] = round((p["inp_price"] + 3 * p["out_price"]) / 4, 6)
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
            "sources": list(SOURCE_NAMES.values()),
            "source_meta": _source_meta(state),
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


def _print_summary(output_models, name_map, dirac_unresolved=None):
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
    if dirac_unresolved:
        print(f"\n  Dirac ids with no matching AA model (skipped, no stub): {len(dirac_unresolved)}")
        for cid in dirac_unresolved:
            print(f"    {cid}")
    print("\n── TOP 20 MODELS (by sources) ──")
    def source_count_for_model(m):
        return len([s_ for s_ in m.get("pricing", {}) if m["pricing"][s_]]) + len([s_ for s_ in m.get("benchmarks", {}) if m["benchmarks"][s_]])
    sorted_by_sources = sorted(output_models, key=source_count_for_model, reverse=True)
    for m in sorted_by_sources[:20]:
        p = [s_ for s_ in m.get("pricing", {}) if m["pricing"][s_]]
        b = [s_ for s_ in m.get("benchmarks", {}) if m["benchmarks"][s_]]
        print(f"  {m['id']:40s} P:{','.join(p):25s} B:{','.join(b)}")
    return ok({"model_count": len(output_models), "name_map_size": len(name_map)})


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

    pipeline = (Pipeline(state)
        .then("step_aa", lambda c: step_aa(c))
        .then("step_livebench", lambda c: step_livebench(c))
        .then("step_arena_text", lambda c: step_arena_text(c))
        .then("step_arena_code", lambda c: step_arena_code(c))
        .then("step_openllm", lambda c: step_openllm(c))
        .then("step_openrouter", lambda c: step_openrouter(c))
        .then("step_dirac", lambda c: step_dirac(c))
        .then("step_misc", lambda c: step_misc(c))
        .then("step_name_map", lambda c: step_name_map(c))
        .then("step_write", lambda c: step_write(c))
        .then("print_summary", lambda c: _print_summary(c["output_models"], c["name_map"], c.get("dirac_unresolved"))))
    pipeline.run()

    if pipeline.ctx.get("_failed_step"):
        return err(pipeline.ctx["_error"])

    output_models = pipeline.ctx["output_models"]
    return ok(pipeline.ctx["print_summary"])

if __name__ == "__main__":
    result = run()
    if result.is_err():
        print("REGISTRY BUILD FAILED:", result.error)
        raise SystemExit(1)
