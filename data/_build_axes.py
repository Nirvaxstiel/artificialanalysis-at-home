import json, os, csv, re
from pathlib import Path


def run(ctx=None):
    if ctx and ctx.get("root"):
        BASE = Path(ctx["root"])
    else:
        BASE = Path(__file__).resolve().parent.parent

    REG = os.path.join(BASE, "data", "model_registry.json")
    OUT = os.path.join(BASE, "data", "axes_catalog.json")

    with open(REG) as f:
        reg = json.load(f)

    models = reg["models"]
    model_ids = {m["id"] for m in models}

    axes = []

    # ── AA PRICING AXES ──
    aa_pricing_path = ["pricing", "aa"]
    aa_pricing_axes = [
        ("aa.inp_price", "Input Price ($/Mtok)", "pricing", "$/M tok", False,
         "AA input price per million tokens", ["inp_price", "input_price_per_m"]),
        ("aa.out_price", "Output Price ($/Mtok)", "pricing", "$/M tok", False,
         "AA output price per million tokens", ["out_price", "output_price_per_m"]),
        ("aa.blended", "Blended Price ($/Mtok)", "pricing", "$/M tok", False,
         "AA blended (weighted average) price", ["blended"]),
        ("aa.cache_hit_price", "Cache Read Price ($/Mtok)", "pricing", "$/M tok", False,
         "AA cache read price per million tokens", ["cache_hit_price"]),
        ("aa.cost_per_task", "Cost per Task ($)", "pricing", "$", False,
         "AA estimated cost per standard task", ["cost_per_task"]),
        ("aa.tokens_m", "Tokens per Task (M)", "pricing", "M tokens", True,
         "AA context length / tokens per task", ["tokens_m"]),
        ("aa.useful_cost", "Useful Cost ($)", "pricing", "$", False,
         "AA cost attributable to useful output (non-reasoning)", ["useful_cost"]),
        ("aa.reasoning_tax_pct", "Reasoning Tax (%)", "pricing", "%", False,
         "AA premium percentage paid for reasoning tokens", ["reasoning_tax_pct"]),
    ]

    costseg_path = ["pricing", "aa", "cost_segments"]
    costseg_axes = [
        ("aa.cost_seg_total", "Total Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — total per task", ["total_cost_per_task_usd"]),
        ("aa.cost_seg_answer", "Answer Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — answer tokens", ["answer_usd"]),
        ("aa.cost_seg_reasoning", "Reasoning Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — reasoning tokens", ["reasoning_usd"]),
        ("aa.cost_seg_cache_write", "Cache Write Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — cache write", ["cache_write_usd"]),
        ("aa.cost_seg_cache_hit", "Cache Hit Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — cache read", ["cache_hit_usd"]),
        ("aa.cost_seg_input", "Input Cost per Task ($)", "pricing", "$", False,
         "Cost breakdown — input tokens", ["input_usd"]),
    ]

    for pid, label, typ, unit, hib, desc, aliases in aa_pricing_axes:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in aa_pricing_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(aliases[0] if aliases else pid.split(".")[-1])
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": pid,
            "label": label,
            "source": "AA",
            "type": typ,
            "unit": unit,
            "higher_is_better": hib,
            "description": desc,
            "models_have": count,
            "range": [round(min(vals), 4), round(max(vals), 4)] if vals else None,
            "group": "Pricing Intelligence" if "cost_seg" in pid else "Pricing",
        })

    for pid, label, typ, unit, hib, desc, aliases in costseg_axes:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in costseg_path[:-1]:
                sec = sec.get(k, {})
            sub = sec.get("cost_segments", {})
            if not sub:
                continue
            v = sub.get(aliases[0])
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": pid,
            "label": label,
            "source": "AA",
            "type": typ,
            "unit": unit,
            "higher_is_better": hib,
            "description": desc,
            "models_have": count,
            "range": [round(min(vals), 4), round(max(vals), 4)] if vals else None,
            "group": "Cost Breakdown",
        })

    # ── AA PERFORMANCE AXES ──
    aa_perf_path = ["pricing", "aa"]
    aa_perf_axes = [
        ("aa.speed_tps", "Speed (tokens/s)", "performance", "tok/s", True,
         "AA output speed in tokens per second", ["speed_tps"]),
        ("aa.ttft", "Time to First Token (s)", "performance", "s", False,
         "AA median time to first token in seconds", ["ttft"]),
    ]
    for pid, label, typ, unit, hib, desc, aliases in aa_perf_axes:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in aa_perf_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(aliases[0])
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": pid, "label": label, "source": "AA", "type": typ,
            "unit": unit, "higher_is_better": hib, "description": desc,
            "models_have": count,
            "range": [round(min(vals)), round(max(vals))] if vals else None,
            "group": "Performance",
        })

    # ── AA QUALITY AXES ──
    aa_bench_path = ["benchmarks", "aa"]
    aa_bench_axes = [
        ("aa.intel", "AA Intelligence Score (0-100)", "quality", "points", True,
         "AA composite intelligence score (Pareto index)", ["intel"]),
        ("aa.iq_per_dollar", "IQ per Dollar ($⁻¹)", "quality", "IQ/$", True,
         "AA intelligence per dollar spent", ["iq_per_dollar_pt"]),
        ("aa.iq_per_mtok", "IQ per Million Tokens", "quality", "IQ/Mtok", True,
         "AA intelligence per million tokens", ["iq_per_mtok"]),
        ("aa.iq_per_mtokdollar", "IQ per $Mtok", "quality", "IQ/($·Mtok)", True,
         "AA intelligence per million token-dollars", ["iq_per_mtokdollar"]),
    ]
    for pid, label, typ, unit, hib, desc, aliases in aa_bench_axes:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in aa_bench_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(aliases[0])
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": pid, "label": label, "source": "AA", "type": typ,
            "unit": unit, "higher_is_better": hib, "description": desc,
            "models_have": count,
            "range": [round(min(vals), 4), round(max(vals), 4)] if vals else None,
            "group": "AA Quality",
        })

    # ── LIVEBENCH QUALITY AXES ──
    lb_path = [("benchmarks", "livebench")]
    lb_orig_keys = set()
    for m in models:
        sec = m
        for k in ("benchmarks", "livebench"):
            sec = sec.get(k, {})
        if not sec:
            continue
        for k in sec:
            if k not in ("tasks",) and k != "average":
                lb_orig_keys.add(k)

    lb_labels = {
        "average": ("LiveBench Average", "Overall average across all LiveBench tasks"),
        "reasoning": ("LiveBench Reasoning", "Reasoning category average"),
        "coding": ("LiveBench Coding", "Coding category average"),
        "agentic_coding": ("LiveBench Agentic Coding", "Agentic coding category average"),
        "math": ("LiveBench Math", "Mathematics category average"),
        "data_analysis": ("LiveBench Data Analysis", "Data analysis category average"),
        "language": ("LiveBench Language", "Language understanding category average"),
        "instruction_following": ("LiveBench Instruction Following", "Instruction following category average"),
    }

    lb_lower_to_orig = {}
    for orig in lb_orig_keys:
        low = orig.casefold().replace(" ", "_").replace("-", "_")
        lb_lower_to_orig[low] = orig
    lb_lower_to_orig["average"] = "average"

    lb_cats = ["average"] + sorted(lb_lower_to_orig.keys())
    for cat in lb_cats:
        if cat == "tasks":
            continue
        label, desc = lb_labels.get(cat, (f"LiveBench {cat}", f"LiveBench {cat} category"))
        orig_key = lb_lower_to_orig.get(cat, cat)
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in ("benchmarks", "livebench"):
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(orig_key)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": f"livebench.{cat}",
            "label": label,
            "source": "LiveBench",
            "type": "quality",
            "unit": "points",
            "higher_is_better": True,
            "description": desc,
            "models_have": count,
            "range": [round(min(vals), 2), round(max(vals), 2)] if vals else None,
            "group": "LiveBench",
            "_dict_key": orig_key,
        })

    # ── ARENA TEXT ELO ──
    arena_t_path = ["benchmarks", "arena_text"]
    for metric, label, desc in [
        ("elo", "Arena Text Elo", "Arena AI text leaderboard Elo score"),
        ("ci", "Arena Text CI", "Arena AI text Elo confidence interval"),
        ("votes", "Arena Text Votes", "Arena AI text total votes"),
    ]:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in arena_t_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(metric)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": f"arena_text.{metric}",
            "label": label,
            "source": "Arena Text",
            "type": "quality" if metric == "elo" else "meta",
            "unit": "points" if metric in ("elo", "ci") else "votes",
            "higher_is_better": metric != "ci",
            "description": desc,
            "models_have": count,
            "range": [min(vals), max(vals)] if vals else None,
            "group": "Arena",
        })

    # ── ARENA CODE ELO ──
    arena_c_path = ["benchmarks", "arena_code"]
    for metric, label, desc in [
        ("elo", "Arena Code Elo", "Arena AI code leaderboard Elo score"),
        ("ci", "Arena Code CI", "Arena AI code Elo confidence interval"),
        ("votes", "Arena Code Votes", "Arena AI code total votes"),
    ]:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in arena_c_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(metric)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": f"arena_code.{metric}",
            "label": label,
            "source": "Arena Code",
            "type": "quality" if metric == "elo" else "meta",
            "unit": "points" if metric in ("elo", "ci") else "votes",
            "higher_is_better": metric != "ci",
            "description": desc,
            "models_have": count,
            "range": [min(vals), max(vals)] if vals else None,
            "group": "Arena",
        })

    # ── OPENLLM QUALITY AXES ──
    ollm_path = ["benchmarks", "openllm"]
    ollm_axes_list = [
        ("average", "OpenLLM Average", "OpenLLM average across all eval dimensions"),
        ("ifeval", "IFEval", "OpenLLM instruction following eval"),
        ("bbh", "BBH", "OpenLLM Big-Bench Hard"),
        ("math_lvl_5", "MATH Lvl 5", "OpenLLM MATH Level 5"),
        ("gpqa", "GPQA", "OpenLLM GPQA (graduate-level Q&A)"),
        ("musr", "MUSR", "OpenLLM MUSR (multi-step reasoning)"),
        ("mmlu_pro", "MMLU-PRO", "OpenLLM MMLU Pro"),
    ]
    for key, label, desc in ollm_axes_list:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in ollm_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(key)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": f"openllm.{key}",
            "label": label,
            "source": "OpenLLM v2",
            "type": "quality",
            "unit": "points",
            "higher_is_better": True,
            "description": desc,
            "models_have": count,
            "range": [round(min(vals), 2), round(max(vals), 2)] if vals else None,
            "group": "OpenLLM",
        })

    # ── OPENROUTER PRICING AXES ──
    or_path = ["pricing", "openrouter"]
    or_axes_list = [
        ("inp_price_per_m", "OR Input Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter input price per million tokens"),
        ("out_price_per_m", "OR Output Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter output price per million tokens"),
        ("cache_read_price_per_m", "OR Cache Read Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter cache-read price per million tokens"),
    ]
    for key, label, typ, unit, hib, desc in or_axes_list:
        count = 0
        vals = []
        for m in models:
            sec = m
            for k in or_path:
                sec = sec.get(k, {})
            if not sec:
                continue
            v = sec.get(key)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": f"openrouter.{key}",
            "label": label,
            "source": "OpenRouter",
            "type": typ,
            "unit": unit,
            "higher_is_better": hib,
            "description": desc,
            "models_have": count,
            "range": [round(min(vals), 6), round(max(vals), 4)] if vals else None,
            "group": "OpenRouter Pricing",
        })

    # ── META AXES ──
    meta_paths = [
        ("meta.params_b", "# Params (B)", "meta", "B", True,
         "Model parameter count in billions"),
        ("meta.co2_kg", "CO₂ Cost (kg)", "meta", "kg", False,
         "Estimated CO₂ cost of training"),
    ]
    for mid, label, typ, unit, hib, desc in meta_paths:
        key = mid.split(".")[-1]
        count = 0
        vals = []
        for m in models:
            v = m.get("meta", {}).get(key)
            if v is not None:
                count += 1
                vals.append(v)
        axes.append({
            "id": mid, "label": label, "source": "OpenLLM v2", "type": typ,
            "unit": unit, "higher_is_better": hib, "description": desc,
            "models_have": count,
            "range": [min(vals), max(vals)] if vals else None,
            "group": "Model Meta",
        })

    # 2. SORT AND TAG
    axes.sort(key=lambda a: (a["source"], a["type"], -a["models_have"]))

    for a in axes:
        if a["range"] and a["range"][0] != a["range"][1]:
            a["normalize_range"] = [0, 100]
        else:
            a["normalize_range"] = None

    source_groups = {}
    for a in axes:
        g = a["source"]
        if g not in source_groups:
            source_groups[g] = {"source": g, "axes": [], "count": 0}
        source_groups[g]["axes"].append(a["id"])
        source_groups[g]["count"] += 1

    # HELPER: extract value from model by axis id
    def get_value(m, aid):
        parts = aid.split(".")
        source = parts[0]
        if source == "meta":
            return m.get("meta", {}).get(parts[-1])
        if parts[0] in ("livebench", "arena_text", "arena_code", "openllm"):
            sec = m.get("benchmarks", {}).get(parts[0], {})
            if len(parts) == 2:
                return sec.get(parts[1])
            elif len(parts) == 3:
                sub = sec.get(parts[1], {})
                return sub.get(parts[2])
        elif parts[0] in ("aa", "openrouter"):
            sec = m.get("pricing", {}).get(parts[0], {})
            if len(parts) == 2:
                return sec.get(parts[1])
            elif len(parts) == 3:
                sub = sec.get(parts[1], {})
                return sub.get(parts[2])
        return None

    # 3. BUILD N-AXIS FEASIBILITY MATRIX
    sources_list = sorted(set(a["source"] for a in axes))
    n_axis_pairs = {}
    for s1 in sources_list:
        for s2 in sources_list:
            if s1 >= s2:
                continue
            a1_ids = [a["id"] for a in axes if a["source"] == s1 and a["type"] != "meta"]
            a2_ids = [a["id"] for a in axes if a["source"] == s2 and a["type"] != "meta"]
            if not a1_ids or not a2_ids:
                continue

            overlap = 0
            for m in models:
                has_s1 = False
                for aid in a1_ids:
                    if get_value(m, aid):
                        has_s1 = True
                        break
                has_s2 = False
                for aid in a2_ids:
                    if get_value(m, aid):
                        has_s2 = True
                        break
                if has_s1 and has_s2:
                    overlap += 1

            if overlap >= 3:
                n_axis_pairs[f"{s1}×{s2}"] = overlap

    # 4. WRITE OUTPUT
    output = {
        "meta": {
            "generated": reg["meta"]["generated"],
            "version": "1.0",
            "total_axes": len(axes),
            "total_models": len(models),
            "sources": list(source_groups.keys()),
            "source_groups": source_groups,
        },
        "axes": axes,
        "feasibility": {
            "n_axis_pairs": n_axis_pairs,
            "notes": "number of models with data from both source groups (non-meta axes only)",
        }
    }

    with open(OUT, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Axes catalog: {len(axes)} axes from {len(source_groups)} sources → {OUT}")
    print(f"  {len(n_axis_pairs)} source-pair overlaps tracked")

    print("\n── AXES BY SOURCE ──")
    for sg_name in sorted(source_groups):
        sg = source_groups[sg_name]
        types = {}
        for a in axes:
            if a["source"] == sg_name:
                t = a["type"]
                types[t] = types.get(t, 0) + 1
        type_str = ", ".join(f"{k}:{v}" for k, v in sorted(types.items()))
        print(f"  {sg_name:15s} {sg['count']:3d} axes  ({type_str})")

    print("\n── CROSS-SOURCE OVERLAP (models with both) ──")
    for pair, count in sorted(n_axis_pairs.items(), key=lambda x: -x[1]):
        print(f"  {pair:40s} {count:4d} models")

    return {"axis_count": len(axes), "source_count": len(source_groups)}

if __name__ == "__main__":
    run()
