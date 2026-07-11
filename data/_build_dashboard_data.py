
import json, re, os
from pathlib import Path

import sys
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from project_axes import ProjectionEngine
from _result import ok, err
from _domain import (
    ProjectionRow, ProjectionRowMeta,
    Archetype, ModelType,
    safe_ppm, safe_cost, safe_tok_per_task, safe_tps, safe_ttft,
    safe_useful_cost, safe_reasoning_tax,
    safe_cost_segment, safe_intel, safe_iq_per_mtok,
    safe_iq_per_mtokdollar, safe_iq_per_dollar,
    safe_elo, safe_ci, safe_votes, safe_benchmark,
    safe_params, safe_carbon, safe_pct,
    safe_ctx_window,
    safe_omniscience, safe_response_time, safe_axis_metric,
    safe_cache,
    try_model_type, try_archetype,
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
    "aa.cost_per_task", "aa.tokens_m", "aa.speed_tps", "aa.ttft",
    "aa.useful_cost", "aa.reasoning_tax_pct",
    "aa.cache_hit_price",
    "aa.intel", "aa.iq_per_mtok", "aa.iq_per_dollar", "aa.iq_per_mtokdollar",
    "aa.aa_coding_index", "aa.aa_math_index", "aa.gpqa", "aa.mmlu_pro",
    "aa.hle", "aa.aime", "aa.aime_25", "aa.math_500", "aa.livecodebench",
    "aa.ifbench", "aa.lcr", "aa.scicode", "aa.tau2", "aa.tau_banking",
    "aa.terminalbench_hard", "aa.terminalbench_v2_1",
    "aa.omniscience_hallucination_rate", "aa.briefcase_analytical_quality_elo",
    "aa.briefcase_presentation_elo", "aa.time_per_task",
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
    "meta.params_total_b", "meta.params_active_b", "meta.release_date",
    "meta.context_window",
    "aa_img.omniscience_index", "aa_img.omniscience_accuracy",
    "aa_img.omniscience_hallucination_rate", "aa_img.briefcase_elo",
    "aa_img.briefcase_analytical_quality_elo", "aa_img.briefcase_presentation_elo",
    "aa_img.briefcase_rubric_score", "aa_img.agentic_index",
    "aa_img.coding_index", "aa_img.openness_index",
    "aa_img.e2e_response_time_s", "aa_img.ttft_variance",
    "dirac.cache_hit_rate_max",
]


def _select_aa_models(raw_rows):
    return [r for r in raw_rows if any(
        k.startswith("aa.") and v is not None
        for k, v in r["axes"].items()
    )]


def _build_projection_row(row, registry_by_id):
    mid = row["id"]
    axes = row["axes"]
    registry = registry_by_id.get(mid, {})
    meta = registry.get("meta", {})

    projection = ProjectionRow(
        slug=mid,
        name=_clean_name(row.get("name")) or mid,
        creator=row.get("creator"),
        type=try_model_type(row.get("model_type")),
        meta=ProjectionRowMeta(
            archetype=try_archetype(meta.get("archetype")),
            pareto_optimal=meta.get("pareto_optimal", False),
            has_breakdown=meta.get("has_breakdown", False),
            cost_percentile=safe_pct(meta.get("cost_percentile")),
            iq_percentile=safe_pct(meta.get("iq_percentile")),
            release_date=meta.get("release_date"),
            confirmed_scraped=meta.get("confirmed_scraped"),
        ),
        inp_price=safe_ppm(axes.get("aa.inp_price")),
        out_price=safe_ppm(axes.get("aa.out_price")),
        blended=safe_ppm(axes.get("aa.blended")),
        cache_hit_price=safe_ppm(axes.get("aa.cache_hit_price")),
        cost_per_task=safe_cost(axes.get("aa.cost_per_task")),
        tokens_m=safe_tok_per_task(axes.get("aa.tokens_m")),
        speed_tps=safe_tps(axes.get("aa.speed_tps")),
        ttft=safe_ttft(axes.get("aa.ttft")),
        useful_cost=safe_useful_cost(axes.get("aa.useful_cost")),
        reasoning_tax_pct=safe_reasoning_tax(axes.get("aa.reasoning_tax_pct")),
        intel=safe_intel(axes.get("aa.intel")),
        iq_per_mtok=safe_iq_per_mtok(axes.get("aa.iq_per_mtok")),
        iq_per_mtokdollar=safe_iq_per_mtokdollar(axes.get("aa.iq_per_mtokdollar")),
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
        aa_coding_index=safe_benchmark(axes.get("aa.aa_coding_index")),
        aa_math_index=safe_benchmark(axes.get("aa.aa_math_index")),
        aa_gpqa=safe_benchmark(axes.get("aa.gpqa")),
        aa_mmlu_pro=safe_benchmark(axes.get("aa.mmlu_pro")),
        aa_hle=safe_benchmark(axes.get("aa.hle")),
        aa_aime=safe_benchmark(axes.get("aa.aime")),
        aa_aime_25=safe_benchmark(axes.get("aa.aime_25")),
        aa_math_500=safe_benchmark(axes.get("aa.math_500")),
        aa_livecodebench=safe_benchmark(axes.get("aa.livecodebench")),
        aa_ifbench=safe_benchmark(axes.get("aa.ifbench")),
        aa_lcr=safe_benchmark(axes.get("aa.lcr")),
        aa_scicode=safe_benchmark(axes.get("aa.scicode")),
        aa_tau2=safe_benchmark(axes.get("aa.tau2")),
        aa_tau_banking=safe_benchmark(axes.get("aa.tau_banking")),
        aa_terminalbench_hard=safe_benchmark(axes.get("aa.terminalbench_hard")),
        aa_terminalbench_v2_1=safe_benchmark(axes.get("aa.terminalbench_v2_1")),
        aa_omniscience_hallucination_rate=safe_benchmark(axes.get("aa.omniscience_hallucination_rate")),
        aa_briefcase_analytical_quality_elo=safe_elo(axes.get("aa.briefcase_analytical_quality_elo")),
        aa_briefcase_presentation_elo=safe_elo(axes.get("aa.briefcase_presentation_elo")),
        aa_time_per_task=safe_response_time(axes.get("aa.time_per_task")),
        openrouter_inp_price_per_m=safe_ppm(axes.get("openrouter.inp_price_per_m")),
        openrouter_out_price_per_m=safe_ppm(axes.get("openrouter.out_price_per_m")),
        openrouter_cache_read_price_per_m=safe_ppm(axes.get("openrouter.cache_read_price_per_m")),
        openrouter_vendor=registry.get("pricing", {}).get("openrouter", {}).get("vendor"),
        params_b=safe_params(meta.get("params_b")),
        params_total_b=safe_params(axes.get("meta.params_total_b")),
        params_active_b=safe_params(axes.get("meta.params_active_b")),
        co2_kg=safe_carbon(axes.get("meta.co2_kg")),
        context_window=safe_ctx_window(meta.get("context_window")),
        cache_hit_rate_max=safe_cache(axes.get("dirac.cache_hit_rate_max")),
        iq_per_dollar_pt=safe_iq_per_dollar(axes.get("aa.iq_per_dollar")),
        omniscience_index=safe_omniscience(axes.get("aa_img.omniscience_index")),
        omniscience_accuracy=safe_benchmark(axes.get("aa_img.omniscience_accuracy")),
        omniscience_hallucination_rate=safe_benchmark(axes.get("aa_img.omniscience_hallucination_rate")),
        briefcase_elo=safe_elo(axes.get("aa_img.briefcase_elo")),
        briefcase_analytical_quality_elo=safe_elo(axes.get("aa_img.briefcase_analytical_quality_elo")),
        briefcase_presentation_elo=safe_elo(axes.get("aa_img.briefcase_presentation_elo")),
        briefcase_rubric_score=safe_benchmark(axes.get("aa_img.briefcase_rubric_score")),
        agentic_index=safe_benchmark(axes.get("aa_img.agentic_index")),
        coding_index=safe_benchmark(axes.get("aa_img.coding_index")),
        openness_index=safe_benchmark(axes.get("aa_img.openness_index")),
        e2e_response_time_s=safe_response_time(axes.get("aa_img.e2e_response_time_s")),
        ttft_variance=safe_axis_metric(axes.get("aa_img.ttft_variance")),
    )

    projection.compute_derived()
    projection.meta.archetype = classify_archetype(projection)

    if projection.tokens_m is not None:
        tokens_m_primitive = projection.tokens_m.as_primitive()
        if tokens_m_primitive <= 0 or tokens_m_primitive > 10_000:
            projection.tokens_m = None

    return projection


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


def _project_rows(engine, axes):
    raw_rows = engine.project(axes)
    aa_models = _select_aa_models(raw_rows)
    registry_by_id = {m["id"]: m for m in engine.models}
    output = [_build_projection_row(r, registry_by_id) for r in aa_models]
    output.sort(key=lambda r: (-(r.intel.as_primitive() if r.intel else 0), r.slug))
    return output


def _build_payload(output):
    return {
        "meta": {
            "generated": _today(),
            "version": "3.0",
            "model_count": len(output),
            "sources": ["AA", "AA_IMG", "Dirac.run", "LiveBench", "Arena Code", "Arena Text", "OpenLLM v2", "OpenRouter"],
            "sources_meta": {
                "AA": {"speculative": False},
                "AA_IMG": {"speculative": True,
                           "note": "Vision-transcribed from AA chart images (future/speculative model projections). Values as-transcribed; some best-effort."},
                "Dirac.run": {"speculative": False,
                              "note": "Observed prefix-cache hit rates per model (max across providers), sourced from dirac.run full table via OpenRouter Effective Pricing."},
                "LiveBench": {"speculative": False},
                "Arena Code": {"speculative": False},
                "Arena Text": {"speculative": False},
                "OpenLLM v2": {"speculative": False},
                "OpenRouter": {"speculative": False},
            },
        },
        "models": output,
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
    state = {"engine": ProjectionEngine()}

    steps = (
        ("project_rows", lambda: ok(_project_rows(state["engine"], _PROJECTION_AXES))),
        ("normalize_radar", lambda: ok(_normalize_radar_scores(state["project_rows"]) or state["project_rows"])),
        ("payload", lambda: ok(_build_payload(state["project_rows"]))),
        ("wrapper", lambda: ok(_build_js_wrapper(state["payload"]))),
        ("write_js", lambda: _write_js(BASE / "processed.js", state["wrapper"])),
    )
    for name, fn in steps:
        r = fn()
        if r.is_err():
            return err(r.error)
        state[name] = r.unwrap()

    _print_dashboard_summary(state["project_rows"])
    return ok(state["payload"])


if __name__ == "__main__":
    result = build()
    if result.is_err():
        print("DASHBOARD BUILD FAILED:", result.error)
        raise SystemExit(1)
