import json, os, csv, re
from pathlib import Path


def _build_axis(models, axis_id, source, label, type_, unit, hib, desc, group,
                path, key=None, range_decimals=None):
    count = 0
    vals = []
    for m in models:
        sec = m
        for k in path:
            sec = sec.get(k, {})
        if not sec:
            continue
        v = sec.get(key if key else axis_id.split(".")[-1])
        if v is not None:
            count += 1
            vals.append(v)
    rng = None
    if vals:
        lo, hi = min(vals), max(vals)
        if range_decimals is not None:
            lo, hi = round(lo, range_decimals), round(hi, range_decimals)
        rng = [lo, hi]
    return {
        "id": axis_id, "label": label, "source": source, "type": type_,
        "unit": unit, "higher_is_better": hib, "description": desc,
        "models_have": count, "range": rng, "group": group,
    }


def _get_value(m, aid):
    parts = aid.split(".")
    source = parts[0]
    if source == "meta":
        return m.get("meta", {}).get(parts[-1])
    if parts[0] in ("livebench", "arena_text", "arena_code", "openllm"):
        sec = m.get("benchmarks", {}).get(parts[0], {})
        if len(parts) == 2:
            return sec.get(parts[1])
        elif len(parts) == 3:
            return sec.get(parts[1], {}).get(parts[2])
    elif parts[0] in ("aa", "openrouter"):
        sec = m.get("pricing", {}).get(parts[0], {})
        if len(parts) == 2:
            return sec.get(parts[1])
        elif len(parts) == 3:
            return sec.get(parts[1], {}).get(parts[2])
    return None


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
    axes = []

    ba = lambda *a, **kw: axes.append(_build_axis(models, *a, **kw))

    # ── AA PRICING ──
    ba("aa.inp_price", "AA", "Input Price ($/Mtok)", "pricing", "$/M tok", False,
      "AA input price per million tokens", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.out_price", "AA", "Output Price ($/Mtok)", "pricing", "$/M tok", False,
      "AA output price per million tokens", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.blended", "AA", "Blended Price ($/Mtok)", "pricing", "$/M tok", False,
      "AA blended (weighted average) price", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.cache_hit_price", "AA", "Cache Read Price ($/Mtok)", "pricing", "$/M tok", False,
      "AA cache read price per million tokens", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.cost_per_task", "AA", "Cost per Task ($)", "pricing", "$", False,
      "AA estimated cost per standard task", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.tokens_m", "AA", "Tokens per Task (M)", "pricing", "M tokens", True,
      "AA context length / tokens per task", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.useful_cost", "AA", "Useful Cost ($)", "pricing", "$", False,
      "AA cost attributable to useful output (non-reasoning)", "Pricing", ["pricing", "aa"], range_decimals=4)
    ba("aa.reasoning_tax_pct", "AA", "Reasoning Tax (%)", "pricing", "%", False,
      "AA premium percentage paid for reasoning tokens", "Pricing", ["pricing", "aa"], range_decimals=4)

    # ── COST BREAKDOWN ──
    cb_path = ["pricing", "aa", "cost_segments"]
    ba("aa.cost_seg_total", "AA", "Total Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — total per task", "Cost Breakdown", cb_path, range_decimals=4)
    ba("aa.cost_seg_answer", "AA", "Answer Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — answer tokens", "Cost Breakdown", cb_path, range_decimals=4)
    ba("aa.cost_seg_reasoning", "AA", "Reasoning Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — reasoning tokens", "Cost Breakdown", cb_path, range_decimals=4)
    ba("aa.cost_seg_cache_write", "AA", "Cache Write Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — cache write", "Cost Breakdown", cb_path, range_decimals=4)
    ba("aa.cost_seg_cache_hit", "AA", "Cache Hit Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — cache read", "Cost Breakdown", cb_path, range_decimals=4)
    ba("aa.cost_seg_input", "AA", "Input Cost per Task ($)", "pricing", "$", False,
      "Cost breakdown — input tokens", "Cost Breakdown", cb_path, range_decimals=4)

    # ── AA PERFORMANCE ──
    perf_path = ["pricing", "aa"]
    ba("aa.speed_tps", "AA", "Speed (tokens/s)", "performance", "tok/s", True,
      "AA output speed in tokens per second", "Performance", perf_path, range_decimals=0)
    ba("aa.ttft", "AA", "Time to First Token (s)", "performance", "s", False,
      "AA median time to first token in seconds", "Performance", perf_path, range_decimals=0)

    # ── AA QUALITY ──
    qual_path = ["benchmarks", "aa"]
    ba("aa.intel", "AA", "AA Intelligence Score (0-100)", "quality", "points", True,
      "AA composite intelligence score (Pareto index)", "AA Quality", qual_path, range_decimals=4)
    ba("aa.iq_per_dollar", "AA", "IQ per Dollar ($⁻¹)", "quality", "IQ/$", True,
      "AA intelligence per dollar spent", "AA Quality", qual_path, range_decimals=4)
    ba("aa.iq_per_mtok", "AA", "IQ per Million Tokens", "quality", "IQ/Mtok", True,
      "AA intelligence per million tokens", "AA Quality", qual_path, range_decimals=4)
    ba("aa.iq_per_mtokdollar", "AA", "IQ per $Mtok", "quality", "IQ/($·Mtok)", True,
      "AA intelligence per million token-dollars", "AA Quality", qual_path, range_decimals=4)

    # ── AA IMAGE CHARTS (vision-transcribed) ──
    img_qual_path = ["benchmarks", "aa_img"]
    for aid, label, unit, hib, desc in [
        ("aa_img.omniscience_index", "AA Omniscience Index", "points", True,
         "AA omniscience index (-100..100): rewards correct, penalizes hallucination"),
        ("aa_img.omniscience_accuracy", "Omniscience Accuracy (%)", "%", True,
         "AA omniscience share of questions answered correctly"),
        ("aa_img.omniscience_hallucination_rate", "Omniscience Hallucination (%)", "%", False,
         "AA omniscience incorrect / (incorrect + partial + not attempted)"),
        ("aa_img.briefcase_elo", "Briefcase Elo", "points", True,
         "AA-Briefcase agentic knowledge-work Elo (rubric + analytical + presentation)"),
        ("aa_img.briefcase_analytical_quality_elo", "Briefcase Analytical Elo", "points", True,
         "AA-Briefcase analytical quality Elo"),
        ("aa_img.briefcase_presentation_elo", "Briefcase Presentation Elo", "points", True,
         "AA-Briefcase presentation Elo"),
        ("aa_img.briefcase_rubric_score", "Briefcase Rubric (%)", "%", True,
         "AA-Briefcase rubric pass rate"),
        ("aa_img.agentic_index", "Agentic Index", "points", True,
         "AA agentic capabilities index (0-100)"),
        ("aa_img.coding_index", "Coding Index", "points", True,
         "AA coding index (0-100), weighted Terminal-Bench + SciCode"),
        ("aa_img.openness_index", "Openness Index", "points", True,
         "AA openness index (0-100), higher = more open"),
        ("aa_img.e2e_response_time_s", "End-to-End Response Time (s)", "s", False,
         "AA time to output 500 tokens (incl. thinking)"),
        ("aa_img.ttft_variance", "TTFT Variance (s)", "s", False,
         "AA time-to-first-token variance (lower = more stable)"),
    ]:
        axes.append(_build_axis(
            models, aid, "AA_IMG", label, "quality", unit, hib, desc,
            "AA Image Charts", img_qual_path, range_decimals=4))

    for aid, label, hib, desc in [
        ("meta.params_total_b", "Total Parameters (B)", True,
         "Model total parameter count in billions (from AA image charts)"),
        ("meta.params_active_b", "Active Parameters (B)", True,
         "Model active (inference) parameter count in billions (from AA image charts)"),
    ]:
        axes.append(_build_axis(
            models, aid, "AA_IMG", label, "meta", "B", hib, desc,
            "AA Image Charts", ["meta"]))

    # ── LIVEBENCH ──
    lb_orig_keys = set()
    for m in models:
        sec = m.get("benchmarks", {}).get("livebench", {})
        if sec:
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

    for cat in ["average"] + sorted(lb_lower_to_orig.keys()):
        if cat == "tasks":
            continue
        label, desc = lb_labels.get(cat, (f"LiveBench {cat}", f"LiveBench {cat} category"))
        orig_key = lb_lower_to_orig.get(cat, cat)
        axes.append(_build_axis(
            models, f"livebench.{cat}", "LiveBench", label, "quality", "points", True, desc,
            "LiveBench", ["benchmarks", "livebench"], key=orig_key, range_decimals=2,
        ))
        axes[-1]["_dict_key"] = orig_key

    # ── ARENA TEXT ──
    arena_t_path = ["benchmarks", "arena_text"]
    for metric, label, desc in [
        ("elo", "Arena Text Elo", "Arena AI text leaderboard Elo score"),
        ("ci", "Arena Text CI", "Arena AI text Elo confidence interval"),
        ("votes", "Arena Text Votes", "Arena AI text total votes"),
    ]:
        a = _build_axis(models, f"arena_text.{metric}", "Arena Text", label,
                        "quality" if metric == "elo" else "meta",
                        "points" if metric in ("elo", "ci") else "votes",
                        metric != "ci", desc, "Arena", arena_t_path)
        axes.append(a)

    # ── ARENA CODE ──
    arena_c_path = ["benchmarks", "arena_code"]
    for metric, label, desc in [
        ("elo", "Arena Code Elo", "Arena AI code leaderboard Elo score"),
        ("ci", "Arena Code CI", "Arena AI code Elo confidence interval"),
        ("votes", "Arena Code Votes", "Arena AI code total votes"),
    ]:
        a = _build_axis(models, f"arena_code.{metric}", "Arena Code", label,
                        "quality" if metric == "elo" else "meta",
                        "points" if metric in ("elo", "ci") else "votes",
                        metric != "ci", desc, "Arena", arena_c_path)
        axes.append(a)

    # ── OPENLLM ──
    ollm_path = ["benchmarks", "openllm"]
    for key, label, desc in [
        ("average", "OpenLLM Average", "OpenLLM average across all eval dimensions"),
        ("ifeval", "IFEval", "OpenLLM instruction following eval"),
        ("bbh", "BBH", "OpenLLM Big-Bench Hard"),
        ("math_lvl_5", "MATH Lvl 5", "OpenLLM MATH Level 5"),
        ("gpqa", "GPQA", "OpenLLM GPQA (graduate-level Q&A)"),
        ("musr", "MUSR", "OpenLLM MUSR (multi-step reasoning)"),
        ("mmlu_pro", "MMLU-PRO", "OpenLLM MMLU Pro"),
    ]:
        axes.append(_build_axis(
            models, f"openllm.{key}", "OpenLLM v2", label, "quality", "points", True, desc,
            "OpenLLM", ollm_path, range_decimals=2))

    # ── OPENROUTER ──
    or_path = ["pricing", "openrouter"]
    for key, label, typ, unit, hib, desc in [
        ("inp_price_per_m", "OR Input Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter input price per million tokens"),
        ("out_price_per_m", "OR Output Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter output price per million tokens"),
        ("cache_read_price_per_m", "OR Cache Read Price ($/Mtok)", "pricing", "$/M tok", False,
         "OpenRouter cache-read price per million tokens"),
    ]:
        axes.append(_build_axis(
            models, f"openrouter.{key}", "OpenRouter", label, typ, unit, hib, desc,
            "OpenRouter Pricing", or_path,
            range_decimals=6 if key == "inp_price_per_m" else 4))

    # ── META ──
    for mid, label, typ, unit, hib, desc in [
        ("meta.params_b", "# Params (B)", "meta", "B", True,
         "Model parameter count in billions"),
        ("meta.co2_kg", "CO₂ Cost (kg)", "meta", "kg", False,
         "Estimated CO₂ cost of training"),
    ]:
        axes.append(_build_axis(
            models, mid, "OpenLLM v2", label, typ, unit, hib, desc,
            "Model Meta", ["meta"]))

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
                has_s1 = any(_get_value(m, aid) for aid in a1_ids)
                has_s2 = any(_get_value(m, aid) for aid in a2_ids)
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
