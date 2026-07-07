"""Build processed.js — flat enriched model data from projection engine.

Usage: python data/_build_dashboard_data.py
Output: data/processed.js (overwritten)

Each model gets ALL available cross-source fields flattened into a single row,
preserving backward-compat with existing viz that read AA-only fields.
"""

import json, sys, os
from pathlib import Path

# Ensure we can import from sibling directory
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from project_axes import ProjectionEngine

def _safe(v, default=None):
    """Return v unless it's NaN or None."""
    if v is None:
        return default
    if isinstance(v, float) and (v != v):  # NaN check
        return default
    return v

def _clean_name(name):
    """Strip parenthetical qualifiers for display."""
    if not name:
        return None
    import re
    return re.sub(r'\s*\((xhigh|high|medium|low|with fallback|max)\)\s*', '', name, flags=re.IGNORECASE).strip()

def _today():
    """Return today's date as YYYY-MM-DD string."""
    from datetime import date
    return date.today().isoformat()

def build(ctx=None):
    pe = ProjectionEngine()
    
    # All axis IDs we want to fetch
    ALL_AXES = [
        # AA pricing
        "aa.inp_price", "aa.out_price", "aa.blended",
        "aa.cost_per_task", "aa.tokens_m", "aa.speed_tps",
        "aa.cost_per_wallsec", "aa.useful_cost", "aa.reasoning_tax_pct",
        "aa.cache",
        # AA benchmarks
        "aa.intel", "aa.iq_per_mtok", "aa.iq_per_dollar", "aa.iq_per_mtokdollar",
        # AA cost segments
        "aa.cost_seg_total", "aa.cost_seg_answer", "aa.cost_seg_reasoning",
        "aa.cost_seg_cache_write", "aa.cost_seg_cache_hit", "aa.cost_seg_input",
        # LiveBench
        "livebench.average", "livebench.coding", "livebench.reasoning",
        "livebench.mathematics", "livebench.language", "livebench.data_analysis",
        "livebench.agentic_coding", "livebench.if",
        # Arena
        "arena_code.elo", "arena_code.ci", "arena_code.votes",
        "arena_text.elo", "arena_text.ci", "arena_text.votes",
        # OpenLLM
        "openllm.average", "openllm.ifeval", "openllm.bbh",
        "openllm.math_lvl_5", "openllm.gpqa", "openllm.musr", "openllm.mmlu_pro",
        # OpenRouter
        "openrouter.inp_price_per_m", "openrouter.out_price_per_m",
        "openrouter.cache_read_price_per_m",
        # Meta
        "meta.params_b", "meta.co2_kg",
    ]
    
    # Only consider models that have AA data (pricing or benchmarks)
    raw = pe.project(ALL_AXES)
    aa_models = [r for r in raw if any(
        k.startswith("aa.") and v is not None
        for k, v in r["axes"].items()
    )]
    
    # Also need to fetch meta fields which are on the registry model, not through axes
    # Build a lookup from model ID to full registry model
    reg_by_id = {m["id"]: m for m in pe.models}
    
    output = []
    for r in aa_models:
        mid = r["id"]
        a = r["axes"]
        reg = reg_by_id.get(mid, {})
        meta = reg.get("meta", {})
        
        cost_task = _safe(a.get("aa.cost_per_task"))
        intel = _safe(a.get("aa.intel"))
        tokens_m = _safe(a.get("aa.tokens_m"))
        
        # Compute derived fields
        iq_per_dollar = _safe(a.get("aa.iq_per_dollar"))
        iq_per_mtok = _safe(a.get("aa.iq_per_mtok"))
        iq_per_mtokdollar = _safe(a.get("aa.iq_per_mtokdollar"))
        reasoning_tax = _safe(a.get("aa.reasoning_tax_pct"))
        
        model = {
            # Core identity
            "slug": mid,
            "name": _clean_name(r.get("name")),
            "creator": r.get("creator"),
            "type": r.get("model_type"),
            
            # AA fields (backward compat)
            "intel": intel,
            "cost_per_task": cost_task,
            "tokens_m": tokens_m,
            "speed_tps": _safe(a.get("aa.speed_tps")),
            "inp_price": _safe(a.get("aa.inp_price")),
            "out_price": _safe(a.get("aa.out_price")),
            "iq_per_dollar_pt": iq_per_dollar,
            "iq_per_mtok": iq_per_mtok,
            "iq_per_mtokdollar": iq_per_mtokdollar,
            "useful_cost": _safe(a.get("aa.useful_cost")),
            "reasoning_tax_pct": reasoning_tax,
            "cost_per_wallsec": _safe(a.get("aa.cost_per_wallsec")),
            "archetype": meta.get("archetype"),
            "has_breakdown": meta.get("has_breakdown", False),
            "pareto_optimal": meta.get("pareto_optimal", False),
            "cost_percentile": _safe(meta.get("cost_percentile")),
            "iq_percentile": _safe(meta.get("iq_percentile")),
            
            # New: cost segment data (rename for clarity)
            "cost_seg_total": _safe(a.get("aa.cost_seg_total")),
            "cost_seg_answer": _safe(a.get("aa.cost_seg_answer")),
            "cost_seg_reasoning": _safe(a.get("aa.cost_seg_reasoning")),
            "cost_seg_cache_write": _safe(a.get("aa.cost_seg_cache_write")),
            "cost_seg_cache_hit": _safe(a.get("aa.cost_seg_cache_hit")),
            "cost_seg_input": _safe(a.get("aa.cost_seg_input")),
            
            # New: LiveBench
            "livebench_average": _safe(a.get("livebench.average")),
            "livebench_coding": _safe(a.get("livebench.coding")),
            "livebench_reasoning": _safe(a.get("livebench.reasoning")),
            "livebench_mathematics": _safe(a.get("livebench.mathematics")),
            "livebench_language": _safe(a.get("livebench.language")),
            "livebench_data_analysis": _safe(a.get("livebench.data_analysis")),
            "livebench_agentic_coding": _safe(a.get("livebench.agentic_coding")),
            "livebench_if": _safe(a.get("livebench.if")),
            
            # New: Arena
            "arena_code_elo": _safe(a.get("arena_code.elo")),
            "arena_code_ci": _safe(a.get("arena_code.ci")),
            "arena_code_votes": _safe(a.get("arena_code.votes")),
            "arena_text_elo": _safe(a.get("arena_text.elo")),
            "arena_text_ci": _safe(a.get("arena_text.ci")),
            "arena_text_votes": _safe(a.get("arena_text.votes")),
            
            # New: OpenLLM
            "openllm_average": _safe(a.get("openllm.average")),
            "openllm_ifeval": _safe(a.get("openllm.ifeval")),
            "openllm_bbh": _safe(a.get("openllm.bbh")),
            "openllm_math_lvl_5": _safe(a.get("openllm.math_lvl_5")),
            "openllm_gpqa": _safe(a.get("openllm.gpqa")),
            "openllm_musr": _safe(a.get("openllm.musr")),
            "openllm_mmlu_pro": _safe(a.get("openllm.mmlu_pro")),
            
            # New: OpenRouter
            "openrouter_inp_price_per_m": _safe(a.get("openrouter.inp_price_per_m")),
            "openrouter_out_price_per_m": _safe(a.get("openrouter.out_price_per_m")),
            "openrouter_cache_read_price_per_m": _safe(a.get("openrouter.cache_read_price_per_m")),
            "openrouter_vendor": _safe(reg.get("pricing", {}).get("openrouter", {}).get("vendor")),
            
            # New: Meta
            "params_b": _safe(a.get("meta.params_b")),
            "co2_kg": _safe(a.get("meta.co2_kg")),
        }
        
        # Derived: iq_per_1k_pt (used by leaderboard)
        if intel is not None and cost_task is not None and cost_task > 0:
            model["iq_per_1k_pt"] = round(intel / cost_task * 1000, 1)
        else:
            model["iq_per_1k_pt"] = None
        
        # Derived: cost_per_iq_pt
        if intel is not None and intel > 0 and cost_task is not None:
            model["cost_per_iq_pt"] = round(cost_task / intel, 6)
        else:
            model["cost_per_iq_pt"] = None
        
        output.append(model)
    
    # Sort: by iq descending, then name
    output.sort(key=lambda m: (-(m["intel"] or 0), m["slug"]))
    
    payload = {
        "meta": {
            "generated": _today(),
            "version": "3.0",
            "model_count": len(output),
            "sources": ["AA", "LiveBench", "Arena Code", "Arena Text", "OpenLLM v2", "OpenRouter"],
        },
        "models": output,
    }
    
    # Write data/processed.js (JS assignment for HTML consumption)
    js_path = BASE / "processed.js"
    with open(js_path, "w") as f:
        f.write("window.PROCESSED_DATA = ")
        json.dump(output, f, indent=2)
        f.write(";\n")
    
    print(f"✅ Wrote {len(output)} models to {js_path}")
    print(f"   With AA intel: {sum(1 for m in output if m['intel'] is not None)}")
    print(f"   With LiveBench avg: {sum(1 for m in output if m['livebench_average'] is not None)}")
    print(f"   With Arena Code elo: {sum(1 for m in output if m['arena_code_elo'] is not None)}")
    print(f"   With Arena Text elo: {sum(1 for m in output if m['arena_text_elo'] is not None)}")
    print(f"   With OpenRouter price: {sum(1 for m in output if m['openrouter_inp_price_per_m'] is not None)}")
    print(f"   With cost breakdown: {sum(1 for m in output if m['cost_seg_total'] is not None)}")
    
    return payload

if __name__ == "__main__":
    build()
