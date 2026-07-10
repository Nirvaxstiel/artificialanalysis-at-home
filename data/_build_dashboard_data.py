
import json, re, os
from pathlib import Path

import sys
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from project_axes import ProjectionEngine
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
    try_model_type, try_archetype,
)


def _clean_name(name):
    """Strip parenthetical qualifiers for display."""
    if not name:
        return None
    return re.sub(
        r'\s*\((xhigh|high|medium|low|with fallback|max)\)\s*',
        '', name, flags=re.IGNORECASE
    ).strip()


def _today():
    from datetime import date
    return date.today().isoformat()


# ── Archetype classification ──

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


def build(ctx=None):
    pe = ProjectionEngine()

    ALL_AXES = [
        "aa.inp_price", "aa.out_price", "aa.blended",
        "aa.cost_per_task", "aa.tokens_m", "aa.speed_tps", "aa.ttft",
        "aa.useful_cost", "aa.reasoning_tax_pct",
        "aa.cache_hit_price",
        "aa.intel", "aa.iq_per_mtok", "aa.iq_per_dollar", "aa.iq_per_mtokdollar",
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
        "meta.params_total_b", "meta.params_active_b",
        "aa_img.omniscience_index", "aa_img.omniscience_accuracy",
        "aa_img.omniscience_hallucination_rate", "aa_img.briefcase_elo",
        "aa_img.briefcase_analytical_quality_elo", "aa_img.briefcase_presentation_elo",
        "aa_img.briefcase_rubric_score", "aa_img.agentic_index",
        "aa_img.coding_index", "aa_img.openness_index",
        "aa_img.e2e_response_time_s", "aa_img.ttft_variance",
    ]

    raw = pe.project(ALL_AXES)
    aa_models = [r for r in raw if any(
        k.startswith("aa.") and v is not None
        for k, v in r["axes"].items()
    )]

    reg_by_id = {m["id"]: m for m in pe.models}

    output = []
    for r in aa_models:
        mid = r["id"]
        a = r["axes"]
        reg = reg_by_id.get(mid, {})
        meta = reg.get("meta", {})

        row = ProjectionRow(
            slug=mid,
            name=_clean_name(r.get("name")) or mid,
            creator=r.get("creator"),
            type=try_model_type(r.get("model_type")),
            meta=ProjectionRowMeta(
                archetype=try_archetype(meta.get("archetype")),
                pareto_optimal=meta.get("pareto_optimal", False),
                has_breakdown=meta.get("has_breakdown", False),
                cost_percentile=safe_pct(meta.get("cost_percentile")),
                iq_percentile=safe_pct(meta.get("iq_percentile")),
            ),
            inp_price=safe_ppm(a.get("aa.inp_price")),
            out_price=safe_ppm(a.get("aa.out_price")),
            blended=safe_ppm(a.get("aa.blended")),
            cache_hit_price=safe_ppm(a.get("aa.cache_hit_price")),
            cost_per_task=safe_cost(a.get("aa.cost_per_task")),
            tokens_m=safe_tok_per_task(a.get("aa.tokens_m")),
            speed_tps=safe_tps(a.get("aa.speed_tps")),
            ttft=safe_ttft(a.get("aa.ttft")),
            useful_cost=safe_useful_cost(a.get("aa.useful_cost")),
            reasoning_tax_pct=safe_reasoning_tax(a.get("aa.reasoning_tax_pct")),
            intel=safe_intel(a.get("aa.intel")),
            iq_per_dollar_pt=safe_iq_per_dollar(a.get("aa.iq_per_dollar")),
            iq_per_mtok=safe_iq_per_mtok(a.get("aa.iq_per_mtok")),
            iq_per_mtokdollar=safe_iq_per_mtokdollar(a.get("aa.iq_per_mtokdollar")),
            cost_seg_total=safe_cost_segment(a.get("aa.cost_seg_total")),
            cost_seg_answer=safe_cost_segment(a.get("aa.cost_seg_answer")),
            cost_seg_reasoning=safe_cost_segment(a.get("aa.cost_seg_reasoning")),
            cost_seg_cache_write=safe_cost_segment(a.get("aa.cost_seg_cache_write")),
            cost_seg_cache_hit=safe_cost_segment(a.get("aa.cost_seg_cache_hit")),
            cost_seg_input=safe_cost_segment(a.get("aa.cost_seg_input")),
            livebench_average=safe_benchmark(a.get("livebench.average")),
            livebench_coding=safe_benchmark(a.get("livebench.coding")),
            livebench_reasoning=safe_benchmark(a.get("livebench.reasoning")),
            livebench_mathematics=safe_benchmark(a.get("livebench.mathematics")),
            livebench_language=safe_benchmark(a.get("livebench.language")),
            livebench_data_analysis=safe_benchmark(a.get("livebench.data_analysis")),
            livebench_agentic_coding=safe_benchmark(a.get("livebench.agentic_coding")),
            livebench_if=safe_benchmark(a.get("livebench.if")),
            arena_code_elo=safe_elo(a.get("arena_code.elo")),
            arena_code_ci=safe_ci(a.get("arena_code.ci")),
            arena_code_votes=safe_votes(a.get("arena_code.votes")),
            arena_text_elo=safe_elo(a.get("arena_text.elo")),
            arena_text_ci=safe_ci(a.get("arena_text.ci")),
            arena_text_votes=safe_votes(a.get("arena_text.votes")),
            openllm_average=safe_benchmark(a.get("openllm.average")),
            openllm_ifeval=safe_benchmark(a.get("openllm.ifeval")),
            openllm_bbh=safe_benchmark(a.get("openllm.bbh")),
            openllm_math_lvl_5=safe_benchmark(a.get("openllm.math_lvl_5")),
            openllm_gpqa=safe_benchmark(a.get("openllm.gpqa")),
            openllm_musr=safe_benchmark(a.get("openllm.musr")),
            openllm_mmlu_pro=safe_benchmark(a.get("openllm.mmlu_pro")),
            openrouter_inp_price_per_m=safe_ppm(a.get("openrouter.inp_price_per_m")),
            openrouter_out_price_per_m=safe_ppm(a.get("openrouter.out_price_per_m")),
            openrouter_cache_read_price_per_m=safe_ppm(a.get("openrouter.cache_read_price_per_m")),
            openrouter_vendor=reg.get("pricing", {}).get("openrouter", {}).get("vendor"),
            params_b=safe_params(a.get("meta.params_b")),
            params_total_b=safe_params(a.get("meta.params_total_b")),
            params_active_b=safe_params(a.get("meta.params_active_b")),
            co2_kg=safe_carbon(a.get("meta.co2_kg")),
            context_window=safe_ctx_window(meta.get("context_window")),
            omniscience_index=safe_omniscience(a.get("aa_img.omniscience_index")),
            omniscience_accuracy=safe_benchmark(a.get("aa_img.omniscience_accuracy")),
            omniscience_hallucination_rate=safe_benchmark(a.get("aa_img.omniscience_hallucination_rate")),
            briefcase_elo=safe_elo(a.get("aa_img.briefcase_elo")),
            briefcase_analytical_quality_elo=safe_elo(a.get("aa_img.briefcase_analytical_quality_elo")),
            briefcase_presentation_elo=safe_elo(a.get("aa_img.briefcase_presentation_elo")),
            briefcase_rubric_score=safe_benchmark(a.get("aa_img.briefcase_rubric_score")),
            agentic_index=safe_benchmark(a.get("aa_img.agentic_index")),
            coding_index=safe_benchmark(a.get("aa_img.coding_index")),
            openness_index=safe_benchmark(a.get("aa_img.openness_index")),
            e2e_response_time_s=safe_response_time(a.get("aa_img.e2e_response_time_s")),
            ttft_variance=safe_axis_metric(a.get("aa_img.ttft_variance")),
        )

        row.compute_derived()
        row.meta.archetype = classify_archetype(row)

        # tokens_m is AA's "Output Tokens per Intelligence Index Task" (millions).
        # It spans the ENTIRE eval suite, not a single context window — so it is
        # legitimately far larger than context_window. Sanity bound only: positive
        # + within AA's observed range (~10M–500M tokens per task).
        if row.tokens_m is not None:
            tm = row.tokens_m.as_primitive()
            if tm <= 0 or tm > 10_000:
                row.tokens_m = None

        output.append(row)

    # Sort: by intel descending, then slug
    output.sort(key=lambda r: (-(r.intel.as_primitive() if r.intel else 0), r.slug))

    # ── Compute radar-normalized scores ──
    def _radar_raws(row):
        intel_raw = row.intel.as_primitive() if row.intel else None
        speed_raw = row.speed_tps.as_primitive() if row.speed_tps else None
        cache_raw = (1 - row.cache_hit_price.as_primitive() / row.inp_price.as_primitive()) \
            if row.cache_hit_price and row.inp_price and row.inp_price.as_primitive() > 0 else None
        cost_raw = 1 / row.cost_per_task.as_primitive() \
            if row.cost_per_task and row.cost_per_task.as_primitive() > 0 else None
        ctx_raw = float(row.context_window.as_primitive()) if row.context_window else None
        return intel_raw, speed_raw, cache_raw, cost_raw, ctx_raw

    all_raws = [_radar_raws(r) for r in output]
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

    payload = {
        "meta": {
            "generated": _today(),
            "version": "3.0",
            "model_count": len(output),
            "sources": ["AA", "AA_IMG", "LiveBench", "Arena Code", "Arena Text", "OpenLLM v2", "OpenRouter"],
            "sources_meta": {
                "AA": {"speculative": False},
                "AA_IMG": {"speculative": True,
                           "note": "Vision-transcribed from AA chart images (future/speculative model projections). Values as-transcribed; some best-effort."},
                "LiveBench": {"speculative": False},
                "Arena Code": {"speculative": False},
                "Arena Text": {"speculative": False},
                "OpenLLM v2": {"speculative": False},
                "OpenRouter": {"speculative": False},
            },
        },
        "models": output,
    }

    # Serialize to processed.js
    rows_dict = [r.to_dict() for r in output]
    wrapper = {
        "sources": payload["meta"]["sources"],
        "sources_meta": payload["meta"]["sources_meta"],
        "models": rows_dict,
    }

    js_path = BASE / "processed.js"
    with open(js_path, "w") as f:
        f.write("window.PROCESSED_DATA = ")
        json.dump(wrapper, f, indent=2)
        f.write(";\n")

    print(f"✅ Wrote {len(output)} models to {js_path}")
    print(f"   With AA intel: {sum(1 for m in output if m.intel is not None)}")
    print(f"   With LiveBench avg: {sum(1 for m in output if m.livebench_average is not None)}")
    print(f"   With Arena Code elo: {sum(1 for m in output if m.arena_code_elo is not None)}")
    print(f"   With Arena Text elo: {sum(1 for m in output if m.arena_text_elo is not None)}")
    print(f"   With OpenRouter price: {sum(1 for m in output if m.openrouter_inp_price_per_m is not None)}")
    print(f"   With cost breakdown: {sum(1 for m in output if m.cost_seg_total is not None)}")

    return payload


if __name__ == "__main__":
    build()
