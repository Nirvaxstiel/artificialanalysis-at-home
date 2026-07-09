"""Build processed.js — flat enriched model data using domain types.

Usage: python data/_build_dashboard_data.py
Output: data/processed.js (overwritten)

Builds ProjectionRow domain objects with typed value objects. Invalid states
are unrepresentable — the row constructor catches them at build time.
"""

import json, re, os
from pathlib import Path

import sys
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from project_axes import ProjectionEngine
from _domain import (
    ProjectionRow, ProjectionRowMeta,
    Archetype, ModelType,
    safe_ppm, safe_cost, safe_tok_per_task, safe_tps,
    safe_wallsec, safe_useful_cost, safe_reasoning_tax,
    safe_cost_segment, safe_intel, safe_iq_per_mtok,
    safe_iq_per_mtokdollar, safe_iq_per_dollar,
    safe_elo, safe_ci, safe_votes, safe_benchmark,
    safe_params, safe_carbon, safe_pct,
    safe_ctx_window,
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


def build(ctx=None):
    pe = ProjectionEngine()

    ALL_AXES = [
        "aa.inp_price", "aa.out_price", "aa.blended",
        "aa.cost_per_task", "aa.tokens_m", "aa.speed_tps",
        "aa.cost_per_wallsec", "aa.useful_cost", "aa.reasoning_tax_pct",
        "aa.cache",
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
            cost_per_task=safe_cost(a.get("aa.cost_per_task")),
            tokens_m=safe_tok_per_task(a.get("aa.tokens_m")),
            speed_tps=safe_tps(a.get("aa.speed_tps")),
            cost_per_wallsec=safe_wallsec(a.get("aa.cost_per_wallsec")),
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
            co2_kg=safe_carbon(a.get("meta.co2_kg")),
            context_window=safe_ctx_window(meta.get("context_window")),
        )

        row.compute_derived()

        # Compute cost_per_wallsec from task cost, speed, tokens if source didn't provide it
        if row.cost_per_wallsec is None:
            ct = row.cost_per_task.as_primitive() if row.cost_per_task else None
            sp = row.speed_tps.as_primitive() if row.speed_tps else None
            tm = row.tokens_m.as_primitive() if row.tokens_m else None
            if ct is not None and ct > 0 and sp is not None and sp > 0 and tm is not None and tm > 0:
                row.cost_per_wallsec = safe_wallsec(ct * sp / (tm * 1_000_000))

        output.append(row)

    # Sort: by intel descending, then slug
    output.sort(key=lambda r: (-(r.intel.as_primitive() if r.intel else 0), r.slug))

    payload = {
        "meta": {
            "generated": _today(),
            "version": "3.0",
            "model_count": len(output),
            "sources": ["AA", "LiveBench", "Arena Code", "Arena Text", "OpenLLM v2", "OpenRouter"],
        },
        "models": output,
    }

    # Serialize to processed.js
    rows_dict = [r.to_dict() for r in output]

    js_path = BASE / "processed.js"
    with open(js_path, "w") as f:
        f.write("window.PROCESSED_DATA = ")
        json.dump(rows_dict, f, indent=2)
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
