
import json, re, os
from dataclasses import replace
from pathlib import Path

import sys
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from project_axes import ProjectionEngine
from _result import Err, Ok, ok, err
from _pipeline import Pipeline
from _domain import (
    ProjectionRow, ProjectionRowMeta,
    Archetype, ModelType,
    safe_ppm, safe_cost, safe_tps, safe_reasoning_tax,
    safe_cost_segment, safe_intel, safe_finance_accounting_index,
    safe_pass_rate, safe_omniscience,
    safe_elo, safe_ci, safe_votes, safe_benchmark,
    safe_params, safe_carbon,
    safe_ctx_window,
    safe_response_time,
    safe_cache,
    safe_model_family,
    try_model_type,
)


def _write_js(path: Path, wrapper: dict) -> "Ok[None]|Err[str]":
    try:
        with open(path, "w") as f:
            f.write("window.PROCESSED_DATA = ")
            json.dump(wrapper, f, indent=2)
            f.write(";\n")
        return ok(None)
    except OSError as e:  # noqa: BLE001
        return err(f"{path.name}: {e}")


def _clean_name(name):
    if not name:
        return None
    return re.sub(
        r'\s*\((xhigh|high|medium|low|with fallback|max)\)\s*',
        '', name, flags=re.IGNORECASE
    ).strip()


def _today():
    from datetime import date
    return date.today().isoformat()


ArchetypePriority = [
    ("frontier", lambda r: r.intel is not None and r.intel.as_primitive() >= 50),
    ("reasoning", lambda r: r.reasoning_tax_pct is not None and r.reasoning_tax_pct.as_primitive() >= 20),
    ("cheap", lambda r: r.cost_per_task is not None and r.cost_per_task.as_primitive() < 0.50
                and r.intel is not None and r.intel.as_primitive() >= 30),
    ("fast", lambda r: r.speed_tps is not None and r.speed_tps.as_primitive() >= 150),
    ("compact", lambda r: r.params_b is not None
                 and r.params_b.as_primitive() > 0
                 and r.params_b.as_primitive() < 30
                 and r.intel is not None and r.intel.as_primitive() >= 30),
]


def classify_archetype(row: ProjectionRow) -> Archetype:
    for name, pred in ArchetypePriority:
        if pred(row):
            return Archetype(name)
    return Archetype.UNCATEGORIZED


_PROJECTION_AXES = [
    "aa.inp_price", "aa.out_price", "aa.blended",
    "aa.cost_per_task", "aa.speed_tps", "aa.reasoning_tax_pct",
    "aa.cache_hit_price",
    "aa.intel", "aa.finance_accounting_index", "aa.analyst_agent_pass_5",
    "aa.briefcase_elo", "aa.gdpval_elo", "aa.omniscience_index",
    "aa.time_per_task",
    "aa.cost_seg_total", "aa.cost_seg_answer", "aa.cost_seg_reasoning",
    "aa.cost_seg_cache_write", "aa.cost_seg_cache_hit", "aa.cost_seg_input",
    "livebench.average", "livebench.coding", "livebench.reasoning",
    "livebench.mathematics", "livebench.language", "livebench.data_analysis",
    "livebench.agentic_coding", "livebench.if",
    "arena_code.elo", "arena_code.ci", "arena_code.votes",
    "arena_text.elo", "arena_text.ci", "arena_text.votes",
    "openllm.average", "openllm.ifeval", "openllm.bbh",
    "openllm.math_lvl_5", "openllm.gpqa", "openllm.musr", "openllm.mmlu_pro",
    "openrouter.inp_price_per_m", "openrouter.out_price_per_m",
    "openrouter.cache_read_price_per_m",
    "meta.params_b", "meta.co2_kg",
    "meta.release_date",
    "meta.context_window",
    "dirac.cache_hit_rate_max",
]


def _select_aa_models(raw_rows):
    return [r for r in raw_rows if any(
        k.startswith("aa.") and v is not None
        for k, v in r["axes"].items()
    )]


def _build_projection_row(row, registry_by_id) -> Ok[ProjectionRow] | Err[str]:
    mid = row["id"]
    axes = row["axes"]
    registry = registry_by_id.get(mid, {})
    meta = registry.get("meta", {})

    finance_index = safe_finance_accounting_index(axes.get("aa.finance_accounting_index"))
    analyst_pass_rate = safe_pass_rate(axes.get("aa.analyst_agent_pass_5"))
    omniscience_index = safe_omniscience(axes.get("aa.omniscience_index"))
    time_per_task = safe_response_time(axes.get("aa.time_per_task"))
    family = safe_model_family(registry.get("family"))
    for metric, result in (
        ("finance_accounting_index", finance_index),
        ("analyst_agent_pass_5", analyst_pass_rate),
        ("omniscience_index", omniscience_index),
        ("time_per_task", time_per_task),
        ("family", family),
    ):
        if result.is_err():
            return err(f"{mid}.{metric}: {result.error}")

    projection = ProjectionRow(
        slug=mid,
        name=_clean_name(row.get("name")) or mid,
        creator=row.get("creator"),
        family=family.unwrap(),
        type=try_model_type(row.get("model_type")),
        meta=ProjectionRowMeta(
            has_breakdown=any(axes.get(f"aa.cost_seg_{key}") is not None
                              for key in ("answer", "reasoning", "cache_write", "cache_hit", "input")),
            release_date=meta.get("release_date"),
        ),
        inp_price=safe_ppm(axes.get("aa.inp_price")),
        out_price=safe_ppm(axes.get("aa.out_price")),
        blended=safe_ppm(axes.get("aa.blended")),
        cache_hit_price=safe_ppm(axes.get("aa.cache_hit_price")),
        cost_per_task=safe_cost(axes.get("aa.cost_per_task")),
        speed_tps=safe_tps(axes.get("aa.speed_tps")),
        reasoning_tax_pct=safe_reasoning_tax(axes.get("aa.reasoning_tax_pct")),
        intel=safe_intel(axes.get("aa.intel")),
        cost_seg_total=safe_cost_segment(axes.get("aa.cost_seg_total")),
        cost_seg_answer=safe_cost_segment(axes.get("aa.cost_seg_answer")),
        cost_seg_reasoning=safe_cost_segment(axes.get("aa.cost_seg_reasoning")),
        cost_seg_cache_write=safe_cost_segment(axes.get("aa.cost_seg_cache_write")),
        cost_seg_cache_hit=safe_cost_segment(axes.get("aa.cost_seg_cache_hit")),
        cost_seg_input=safe_cost_segment(axes.get("aa.cost_seg_input")),
        livebench_average=safe_benchmark(axes.get("livebench.average")),
        livebench_coding=safe_benchmark(axes.get("livebench.coding")),
        livebench_reasoning=safe_benchmark(axes.get("livebench.reasoning")),
        livebench_mathematics=safe_benchmark(axes.get("livebench.mathematics")),
        livebench_language=safe_benchmark(axes.get("livebench.language")),
        livebench_data_analysis=safe_benchmark(axes.get("livebench.data_analysis")),
        livebench_agentic_coding=safe_benchmark(axes.get("livebench.agentic_coding")),
        livebench_if=safe_benchmark(axes.get("livebench.if")),
        arena_code_elo=safe_elo(axes.get("arena_code.elo")),
        arena_code_ci=safe_ci(axes.get("arena_code.ci")),
        arena_code_votes=safe_votes(axes.get("arena_code.votes")),
        arena_text_elo=safe_elo(axes.get("arena_text.elo")),
        arena_text_ci=safe_ci(axes.get("arena_text.ci")),
        arena_text_votes=safe_votes(axes.get("arena_text.votes")),
        openllm_average=safe_benchmark(axes.get("openllm.average")),
        openllm_ifeval=safe_benchmark(axes.get("openllm.ifeval")),
        openllm_bbh=safe_benchmark(axes.get("openllm.bbh")),
        openllm_math_lvl_5=safe_benchmark(axes.get("openllm.math_lvl_5")),
        openllm_gpqa=safe_benchmark(axes.get("openllm.gpqa")),
        openllm_musr=safe_benchmark(axes.get("openllm.musr")),
        openllm_mmlu_pro=safe_benchmark(axes.get("openllm.mmlu_pro")),
        aa_finance_accounting_index=finance_index.unwrap(),
        aa_analyst_agent_pass_5=analyst_pass_rate.unwrap(),
        aa_briefcase_elo=safe_elo(axes.get("aa.briefcase_elo")),
        aa_gdpval_elo=safe_elo(axes.get("aa.gdpval_elo")),
        aa_omniscience_index=omniscience_index.unwrap(),
        aa_time_per_task=time_per_task.unwrap(),
        openrouter_inp_price_per_m=safe_ppm(axes.get("openrouter.inp_price_per_m")),
        openrouter_out_price_per_m=safe_ppm(axes.get("openrouter.out_price_per_m")),
        openrouter_cache_read_price_per_m=safe_ppm(axes.get("openrouter.cache_read_price_per_m")),
        openrouter_vendor=registry.get("pricing", {}).get("openrouter", {}).get("vendor"),
        params_b=safe_params(meta.get("params_b")),
        co2_kg=safe_carbon(axes.get("meta.co2_kg")),
        context_window=safe_ctx_window(meta.get("context_window")),
        cache_hit_rate_max=safe_cache(axes.get("dirac.cache_hit_rate_max")),
    )

    projection.compute_derived()
    projection.meta.archetype = classify_archetype(projection)
    projection.meta.dirac_cache_hit_rates = meta.get("dirac_cache_hit_rates")
    return ok(projection)


def _extract_radar_raws(row):
    intel_raw = row.intel.as_primitive() if row.intel else None
    speed_raw = row.speed_tps.as_primitive() if row.speed_tps else None
    cache_raw = (1 - row.cache_hit_price.as_primitive() / row.inp_price.as_primitive()) \
        if row.cache_hit_price and row.inp_price and row.inp_price.as_primitive() > 0 else None
    cost_raw = 1 / row.cost_per_task.as_primitive() \
        if row.cost_per_task and row.cost_per_task.as_primitive() > 0 else None
    ctx_raw = float(row.context_window.as_primitive()) if row.context_window else None
    return intel_raw, speed_raw, cache_raw, cost_raw, ctx_raw


def _normalize_radar_scores(output):
    all_raws = [_extract_radar_raws(r) for r in output]
    maxes = []
    for axis_idx in range(5):
        vals = [r[axis_idx] for r in all_raws if r[axis_idx] is not None]
        maxes.append(max(vals) if vals else 1)

    for row, raws in zip(output, all_raws):
        row.radar_intel = (raws[0] / maxes[0]) if raws[0] is not None else None
        row.radar_speed = (raws[1] / maxes[1]) if raws[1] is not None else None
        row.radar_cache_eff = (raws[2] / maxes[2]) if raws[2] is not None else None
        row.radar_cost_eff = (raws[3] / maxes[3]) if raws[3] is not None else None
        row.radar_ctx = (raws[4] / maxes[4]) if raws[4] is not None else None


def _mark_pareto_optimal(rows: list[ProjectionRow]) -> list[ProjectionRow]:
    candidates = sorted(
        (row for row in rows
         if row.cost_per_task is not None
         and row.cost_per_task.as_primitive() > 0
         and row.intel is not None),
        key=lambda row: (
            row.cost_per_task.as_primitive(),
            -row.intel.as_primitive(),
            row.slug,
        ),
    )
    frontier = set()
    best_intel = -float("inf")
    for row in candidates:
        intel = row.intel.as_primitive()
        if intel > best_intel:
            frontier.add(row.slug)
            best_intel = intel + 1e-9
    return [
        replace(row, meta=replace(row.meta, pareto_optimal=row.slug in frontier))
        for row in rows
    ]


def _project_rows(engine, axes) -> Ok[dict] | Err[str]:
    raw_rows = engine.project(axes)
    registry_by_id = {m["id"]: m for m in engine.models}
    output = []
    for raw_row in raw_rows:
        result = _build_projection_row(raw_row, registry_by_id)
        if result.is_err():
            return err(result.error)
        output.append(result.unwrap())
    output.sort(key=lambda r: (-(r.intel.as_primitive() if r.intel else 0), r.slug))
    output = _mark_pareto_optimal(output)
    return ok({"raw_rows": raw_rows, "rows": output})


def _counts(projection):
    aa_rows = _select_aa_models(projection["raw_rows"])
    return {
        "models": len(projection["rows"]),
        "aa_models": len(aa_rows),
        "creators": len({r["creator"] for r in aa_rows if r.get("creator")}),
    }


def _build_payload(projection, registry_meta):
    return {
        "meta": {
            "generated": _today(),
            "version": "3.0",
            "model_count": len(projection["rows"]),
            "counts": _counts(projection),
            "sources": registry_meta.get("sources", []),
            "sources_meta": registry_meta.get("source_meta", {}),
        },
        "models": projection["rows"],
    }


def _build_js_wrapper(payload):
    rows_dict = [r.to_dict() for r in payload["models"]]
    return {
        "meta": payload["meta"],
        "sources": payload["meta"]["sources"],
        "sources_meta": payload["meta"]["sources_meta"],
        "models": rows_dict,
    }


def _print_dashboard_summary(output):
    print(f"✅ Wrote {len(output)} models to processed.js")
    print(f"   With AA intel: {sum(1 for m in output if m.intel is not None)}")
    print(f"   With LiveBench avg: {sum(1 for m in output if m.livebench_average is not None)}")
    print(f"   With Arena Code elo: {sum(1 for m in output if m.arena_code_elo is not None)}")
    print(f"   With Arena Text elo: {sum(1 for m in output if m.arena_text_elo is not None)}")
    print(f"   With OpenRouter price: {sum(1 for m in output if m.openrouter_inp_price_per_m is not None)}")
    print(f"   With cost breakdown: {sum(1 for m in output if m.cost_seg_total is not None)}")


def build(ctx=None):
    repo_root = Path(ctx["root"]) if ctx and ctx.get("root") else BASE.parent
    data_dir = repo_root / "data"
    engine = ProjectionEngine(
        registry_path=str(data_dir / "model_registry.json"),
        axes_path=str(data_dir / "axes_catalog.json"),
    )
    pipeline = (Pipeline({"engine": engine, "js_path": str(data_dir / "processed.js")})
        .then("project_rows", lambda c: _project_rows(c["engine"], _PROJECTION_AXES))
        .then("normalize_radar", lambda c: ok(_normalize_radar_scores(c["project_rows"]["rows"]) or c["project_rows"]))
        .then("payload", lambda c: ok(_build_payload(c["project_rows"], c["engine"].registry.get("meta", {}))))
        .then("wrapper", lambda c: ok(_build_js_wrapper(c["payload"])))
        .then("write_js", lambda c: _write_js(c["js_path"], c["wrapper"])))
    pipeline.run()
    if pipeline.ctx.get("_failed_step"):
        return err(pipeline.ctx["_error"])
    _print_dashboard_summary(pipeline.ctx["project_rows"]["rows"])
    return ok(pipeline.ctx["payload"])


if __name__ == "__main__":
    result = build()
    if result.is_err():
        print("DASHBOARD BUILD FAILED:", result.error)
        raise SystemExit(1)
