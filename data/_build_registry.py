"""Build model_registry.json — merge all sources into unified domain model.

Output: data/model_registry.json
  - models[] with canonical ID, meta, pricing(source-tagged), benchmarks(source-tagged)
  - name_map for cross-reference
"""
import json, csv, os, re
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # repo root
SRC = os.path.join(BASE, "data", "sources")
OUT = os.path.join(BASE, "data", "model_registry.json")

# ═══════════════════════════════════════════════
# 1. CANONICAL NAME MAP
# ═══════════════════════════════════════════════

# Explicit aliases: {source: {source_id: canonical_id}}
# Canonical IDs follow Arena/convention format (dots not hyphens for versions)

AA_TO_CANONICAL = {
    "gpt-oss-20b": "gpt-oss-20b",
    "gpt-oss-120b": "gpt-oss-120b",
    "gpt-5-5-low": "gpt-5.5-low",
    "gpt-5-5-high": "gpt-5.5-high",
    "gpt-5-5-medium": "gpt-5.5-medium",
    "gpt-5-5": "gpt-5.5-xhigh",
    "gpt-5-5-pro": "gpt-5.5-pro",
    "gpt-5-3-codex": "gpt-5.3-codex",
    "gpt-5-2-codex": "gpt-5.2-codex",
    "muse-spark": "muse-spark",
    "gemma-4-31b": "gemma-4-31b",
    "gemini-3-1-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3-5-flash": "gemini-3.5-flash",
    "claude-4-5-haiku-reasoning": "claude-4.5-haiku-reasoning",
    "claude-fable-5": "claude-fable-5",
    "claude-sonnet-5": "claude-sonnet-5",
    "claude-opus-4-8": "claude-opus-4.8",
    "claude-4-5-sonnet-thinking": "claude-4.5-sonnet-thinking",
    "claude-sonnet-4-6-adaptive": "claude-sonnet-4.6-adaptive",
    "mistral-medium-3-5": "mistral-medium-3.5",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "grok-4-3": "grok-4.3",
    "nova-2-0-pro-reasoning-medium": "nova-2.0-pro-reasoning-medium",
    "solar-pro-3": "solar-pro-3",
    "minimax-m2-7": "minimax-m2.7",
    "minimax-m3": "minimax-m3",
    "minimax-m2-5": "minimax-m2.5",
    "nvidia-nemotron-3-ultra-550b-a55b": "nemotron-3-ultra-550b-a55b",
    "nvidia-nemotron-3-super-120b-a12b": "nemotron-3-super-120b-a12b",
    "kimi-k2-7-code": "kimi-k2.7-code",
    "kimi-k2-6": "kimi-k2.6",
    "kimi-k2-thinking": "kimi-k2-thinking",
    "mimo-v2-5-pro": "mimo-v2.5-pro",
    "k2-think-v2": "k2-think-v2",
    "glm-5-2": "glm-5.2",
    "qwen3-5-397b-a17b": "qwen3.5-397b-a17b",
    "qwen3-7-max": "qwen3.7-max",
}

# Build reverse maps for other sources
def aa_slug_to_canonical(slug):
    return AA_TO_CANONICAL.get(slug, slug)

def arena_id_to_canonical(aid):
    """Arena IDs -> canonical. Handle hyphens-vs-dots mismatch."""
    n = aid.strip().lower()
    # Known Arena-to-canonical cross-refs where Arena uses hyphens not dots
    arena_fixes = {
        "claude-opus-4-8": "claude-opus-4.8",
        "claude-opus-4-6": "claude-opus-4.6",
        "claude-opus-4-7": "claude-opus-4.7",
        "claude-4-5-haiku-reasoning": "claude-4.5-haiku-reasoning",
        "claude-4-5-sonnet-thinking": "claude-4.5-sonnet-thinking",
        "claude-sonnet-4-6": "claude-sonnet-4.6",
        "claude-sonnet-4-5-20250929": "claude-sonnet-4.5",
        "grok-4-3": "grok-4.3",
        "grok-4-1": "grok-4.1",
        "gpt-5-5-high": "gpt-5.5-high",
        "gpt-5-5": "gpt-5.5-xhigh",
        "gpt-5-5-pro": "gpt-5.5-pro",
        "gpt-5-4": "gpt-5.4",
        "gpt-5-4-high": "gpt-5.4-high",
        "gpt-5-3-codex": "gpt-5.3-codex",
        "gpt-5-2-codex": "gpt-5.2-codex",
        "gemini-3-5-flash": "gemini-3.5-flash",
        "gemini-3-pro": "gemini-3-pro",
        "gemini-3-1-pro-preview": "gemini-3.1-pro-preview",
        "gemini-3-flash": "gemini-3-flash",
        "mistral-medium-3-5": "mistral-medium-3.5",
        "glm-5-2": "glm-5.2",
        "glm-5-1": "glm-5.1",
        "gpt-5-5-instant": "gpt-5.5-instant",
        "nova-2-0-pro-reasoning-medium": "nova-2.0-pro-reasoning-medium",
        "minimax-m3": "minimax-m3",
    }
    return arena_fixes.get(n, n)

def livebench_name_to_canonical(name):
    """LiveBench names. Mostly same as canonical, except some have dates."""
    n = name.strip().lower()
    # Strip date suffixes like -20250805
    n = re.sub(r'-20\d{6}', '', n)
    # Known aliases not in AA but might match OpenRouter
    return n

def openrouter_id_to_canonical(rid):
    """openai/gpt-5.5-high -> gpt-5.5-high"""
    r = rid.strip().lower()
    parts = r.split("/")
    if len(parts) >= 2:
        return parts[-1]  # Use model name only
    return r

def openllm_name_to_canonical(name):
    """HF model path or display name -> canonical"""
    if not name:
        return None
    n = name.strip()
    # Handle HTML links from parquet
    if "href=" in n:
        m = re.search(r'href="([^"]+)"', n)
        if m:
            n = m.group(1)
    n = n.lower()
    # Strip HF org prefix: openai/gpt-5.5-high -> gpt-5.5-high
    if "/" in n:
        parts = n.split("/")
        # Keep model name part
        n = parts[-1]
    # Strip date suffixes
    n = re.sub(r'-20\d{6}', '', n)
    return n


# ═══════════════════════════════════════════════
# 2. LOAD ALL SOURCES
# ═══════════════════════════════════════════════

today = date.today().isoformat()
all_models = {}  # canonical_id -> model record

# ── AA (from processed.js) ──
aa_js = Path(BASE, "data", "processed.js").read_text()
aa_data = json.loads(aa_js.removeprefix("window.PROCESSED_DATA = ").removesuffix(";\n"))
aa_models = aa_data if isinstance(aa_data, list) else aa_data.get("models", [])

for m in aa_models:
    slug = m.get("slug")
    cid = aa_slug_to_canonical(slug)
    
    all_models[cid] = {
        "id": cid,
        "name": m.get("name"),
        "creator": m.get("creator"),
        "model_type": m.get("type"),
        "meta": {
            "archetype": m.get("archetype"),
            "pareto_optimal": m.get("pareto_optimal", False),
            "cost_percentile": m.get("cost_percentile"),
            "iq_percentile": m.get("iq_percentile"),
            "has_breakdown": m.get("has_breakdown", False),
        },
        "pricing": {
            "aa": {
                "inp_price": m.get("inp_price"),
                "out_price": m.get("out_price"),
                "blended": m.get("inp_price"),  # AA stores blended separately in raw
                "cost_per_task": m.get("cost_per_task"),
                "tokens_m": m.get("tokens_m"),
                "speed_tps": m.get("speed_tps"),
                "cost_per_wallsec": m.get("cost_per_wallsec"),
                "useful_cost": m.get("useful_cost"),
                "reasoning_tax_pct": m.get("reasoning_tax_pct"),
            }
        },
        "benchmarks": {
            "aa": {
                "intel": m.get("intel"),
                "iq_per_dollar_pt": m.get("iq_per_dollar_pt"),
                "iq_per_mtok": m.get("iq_per_mtok"),
                "iq_per_mtokdollar": m.get("iq_per_mtokdollar"),
            }
        },
        "aliases": {
            "aa": slug,
        }
    }

# Inject blended pricing from raw aa_model_data
with open(os.path.join(BASE, "data", "aa_model_data.json")) as f:
    aa_raw = json.load(f)
for slug, raw in aa_raw.items():
    cid = aa_slug_to_canonical(slug)
    if cid in all_models:
        all_models[cid]["pricing"]["aa"]["blended"] = raw.get("blended")
        all_models[cid]["pricing"]["aa"]["cache"] = raw.get("cache")

# ── LIVEBENCH ──
lb_path = os.path.join(SRC, "livebench_2026_01_08.csv")
cat_path = os.path.join(SRC, "livebench_categories_2026_01_08.json")

with open(cat_path) as f:
    lb_categories = json.load(f)

# Build task->category map
task_to_cat = {}
for cat_name, tasks in lb_categories.items():
    for t in tasks:
        task_to_cat[t] = cat_name

with open(lb_path) as f:
    reader = csv.DictReader(f)
    lb_models = list(reader)

for m in lb_models:
    name = m["model"]
    cid = livebench_name_to_canonical(name)
    
    # Map tasks to categories and compute averages
    scores = {}
    cat_scores = {}
    task_count = 0
    for task, val in m.items():
        if task == "model":
            continue
        if val == "" or val is None:
            continue
        try:
            v = float(val)
        except (ValueError, TypeError):
            continue
        scores[task] = v
        
        cat = task_to_cat.get(task, "Other")
        if cat not in cat_scores:
            cat_scores[cat] = []
        cat_scores[cat].append(v)
        task_count += 1
    
    # Category averages
    cat_avgs = {cat: round(sum(vs)/len(vs), 2) for cat, vs in cat_scores.items()}
    overall = round(sum(scores.values()) / len(scores), 2) if scores else None
    
    # Find or create model
    if cid not in all_models:
        all_models[cid] = {
            "id": cid,
            "name": name,
            "creator": None,
            "model_type": None,
            "meta": {},
            "pricing": {},
            "benchmarks": {},
            "aliases": {},
        }
    
    all_models[cid]["aliases"]["livebench"] = name
    all_models[cid]["benchmarks"]["livebench"] = {
        "average": overall,
        **cat_avgs,
        "tasks": scores,
    }


# ── ARENA AI (TEXT) ──
arena_text_path = os.path.join(SRC, "arena_text.json")
with open(arena_text_path) as f:
    arena_text_data = json.load(f)

for m in arena_text_data.get("models", []):
    aid = m["model"]
    cid = arena_id_to_canonical(aid)
    
    if cid not in all_models:
        all_models[cid] = {
            "id": cid,
            "name": aid,
            "creator": m.get("vendor"),
            "model_type": m.get("license"),
            "meta": {},
            "pricing": {},
            "benchmarks": {},
            "aliases": {},
        }
    
    all_models[cid]["aliases"]["arena"] = aid
    all_models[cid]["creator"] = all_models[cid].get("creator") or m.get("vendor")
    all_models[cid]["benchmarks"]["arena_text"] = {
        "elo": m.get("score"),
        "ci": m.get("ci"),
        "votes": m.get("votes"),
    }

# ── ARENA AI (CODE) ──
arena_code_path = os.path.join(SRC, "arena_code.json")
with open(arena_code_path) as f:
    arena_code_data = json.load(f)

for m in arena_code_data.get("models", []):
    aid = m["model"]
    cid = arena_id_to_canonical(aid)
    
    if cid not in all_models:
        all_models[cid] = {
            "id": cid,
            "name": aid,
            "creator": m.get("vendor"),
            "model_type": m.get("license"),
            "meta": {},
            "pricing": {},
            "benchmarks": {},
            "aliases": {},
        }
    
    all_models[cid]["aliases"]["arena_code"] = aid
    all_models[cid]["creator"] = all_models[cid].get("creator") or m.get("vendor")
    all_models[cid]["benchmarks"]["arena_code"] = {
        "elo": m.get("score"),
        "ci": m.get("ci"),
        "votes": m.get("votes"),
    }

# ── COST BREAKDOWN ──
# Map display names in cost_breakdown to canonical IDs
costbd_name_map = {
    "gpt-oss-20b (high)": "gpt-oss-20b",
    "DeepSeek V4 Flash (max)": "deepseek-v4-flash",
    "MiMo-V2.5-Pro (max)": "mimo-v2.5-pro",
    "DeepSeek V4 Pro (max)": "deepseek-v4-pro",
    "gpt-oss-120b (high)": "gpt-oss-120b",
    "MiniMax-M2.7": "minimax-m2.7",
    "MiniMax-M3": "minimax-m3",
    "Grok 4.3 (high)": "grok-4.3",
    "Nova 2.0 Pro Preview (medium)": "nova-2.0-pro-reasoning-medium",
    "Kimi K2.7 Code": "kimi-k2.7-code",
    "GPT-5.5 (low)": "gpt-5.5-low",
    "Claude 4.5 Haiku": "claude-4.5-haiku-reasoning",
    "Nemotron 3 Ultra": "nemotron-3-ultra-550b-a55b",
    "NVIDIA Nemotron 3 Super": "nemotron-3-super-120b-a12b",
    "Gemini 3.1 Pro Preview": "gemini-3.1-pro-preview",
    "Kimi K2.6": "kimi-k2.6",
    "Qwen3.5 397B A17B": "qwen3.5-397b-a17b",
    "Claude 4.5 Sonnet": "claude-4.5-sonnet-thinking",
    "GPT-5.5 (medium)": "gpt-5.5-medium",
    "GLM-5.2 (max)": "glm-5.2",
    "Gemini 3.5 Flash": "gemini-3.5-flash",
    "GPT-5.5 (high)": "gpt-5.5-high",
    "GPT-5.5 (xhigh)": "gpt-5.5-xhigh",
    "Qwen3.7 Max": "qwen3.7-max",
    "Claude Sonnet 4.6 (max)": "claude-sonnet-4.6-adaptive",
    "Mistral Medium 3.5": "mistral-medium-3.5",
    "Claude Opus 4.8 (max)": "claude-opus-4.8",
    "Claude Sonnet 5 (max)": "claude-sonnet-5",
}

costbd_path = os.path.join(BASE, "data", "aa_cost_breakdown.json")
with open(costbd_path) as f:
    costbd_data = json.load(f)

for m in costbd_data.get("models", []):
    display_name = m.get("name", "")
    cid = costbd_name_map.get(display_name)
    if not cid or cid not in all_models:
        continue
    
    all_models[cid]["pricing"]["aa"]["cost_segments"] = {
        "total_cost_per_task_usd": m.get("total_cost_per_task_usd"),
        "answer_usd": m.get("answer_usd"),
        "reasoning_usd": m.get("reasoning_usd"),
        "cache_write_usd": m.get("cache_write_usd"),
        "cache_hit_usd": m.get("cache_hit_usd"),
        "input_usd": m.get("input_usd"),
    }


# ── OPENLLM v2 (AA subset) ──
ollm_path = os.path.join(SRC, "openllm_aa_subset.json")
with open(ollm_path) as f:
    ollm_models = json.load(f)

for m in ollm_models:
    fullname = m.get("fullname", "")
    cid = openllm_name_to_canonical(fullname)
    if not cid:
        continue
    
    if cid not in all_models:
        all_models[cid] = {
            "id": cid,
            "name": fullname,
            "creator": None,
            "model_type": None,
            "meta": {},
            "pricing": {},
            "benchmarks": {},
            "aliases": {},
        }
    
    all_models[cid]["aliases"]["openllm"] = fullname
    all_models[cid]["benchmarks"]["openllm"] = {
        "average": m.get("Average ⬆️"),
        "ifeval": m.get("IFEval"),
        "bbh": m.get("BBH"),
        "math_lvl_5": m.get("MATH Lvl 5"),
        "gpqa": m.get("GPQA"),
        "musr": m.get("MUSR"),
        "mmlu_pro": m.get("MMLU-PRO"),
    }
    
    # Merge metadata
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
        if not all_models[cid]["meta"]:
            all_models[cid]["meta"] = {}
        all_models[cid]["meta"].update(meta_updates)


# ── OPENROUTER ──
or_path = os.path.join(SRC, "openrouter_models.json")
with open(or_path) as f:
    or_models = json.load(f)

for m in or_models:
    rid = m["id"]
    cid = openrouter_id_to_canonical(rid)
    
    if cid not in all_models:
        all_models[cid] = {
            "id": cid,
            "name": m.get("name", rid),
            "creator": m.get("vendor"),
            "model_type": None,
            "meta": {},
            "pricing": {},
            "benchmarks": {},
            "aliases": {},
        }
    
    all_models[cid]["aliases"]["openrouter"] = rid
    all_models[cid]["pricing"]["openrouter"] = {}
    
    # Convert prices (OpenRouter uses $/token, AA uses $/M tokens)
    def or_price(price_str):
        if price_str is None or price_str == "" or float(price_str) < 0:
            return None
        return float(price_str)
    
    inp = or_price(m.get("input_price"))
    out = or_price(m.get("output_price"))
    cache = or_price(m.get("cache_read_price"))
    
    if inp is not None:
        all_models[cid]["pricing"]["openrouter"]["inp_price"] = inp  # $/token
        all_models[cid]["pricing"]["openrouter"]["inp_price_per_m"] = inp * 1_000_000  # $/Mtok
    if out is not None:
        all_models[cid]["pricing"]["openrouter"]["out_price"] = out
        all_models[cid]["pricing"]["openrouter"]["out_price_per_m"] = out * 1_000_000
    if cache is not None:
        all_models[cid]["pricing"]["openrouter"]["cache_read_price"] = cache
        all_models[cid]["pricing"]["openrouter"]["cache_read_price_per_m"] = cache * 1_000_000
    
    all_models[cid]["pricing"]["openrouter"]["vendor"] = m.get("vendor")


# ═══════════════════════════════════════════════
# 3. BUILD NAME MAP (source_id -> canonical_id)
# ═══════════════════════════════════════════════

name_map = {}
for cid, model in all_models.items():
    for source, sid in model.get("aliases", {}).items():
        key = f"{source}:{sid}"
        name_map[key] = cid


# ═══════════════════════════════════════════════
# 4. WRITE OUTPUT
# ═══════════════════════════════════════════════

# Remove the "aliases" field from output models (it's in name_map)
# But keep it for debugging? Let's keep it but make it less prominent.
output_models = []
for cid in sorted(all_models.keys()):
    model = all_models[cid]
    # Drop raw task scores from livebench to keep output clean
    if "livebench" in model.get("benchmarks", {}):
        lb = model["benchmarks"]["livebench"]
        if "tasks" in lb:
            del lb["tasks"]
    output_models.append(model)

output = {
    "meta": {
        "generated": today,
        "version": "1.0",
        "model_count": len(output_models),
        "source_count": {
            "aa": len(aa_models),
            "livebench": len(lb_models),
            "arena_text": len(arena_text_data.get("models", [])),
            "arena_code": len(arena_code_data.get("models", [])),
            "openllm_aa_subset": len(ollm_models),
            "openrouter": len(or_models),
        },
        "sources": ["AA", "LiveBench", "Arena Text", "Arena Code", "OpenLLM v2", "OpenRouter", "Cost Breakdown"],
        "aa_index_version": aa_data.get("meta", {}).get("aa_index_version"),
        "name_map_size": len(name_map),
    },
    "name_map": name_map,
    "models": output_models,
}

with open(OUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"Written {len(output_models)} models to {OUT}")
print(f"Name map: {len(name_map)} alias entries")
print(f"Model registry size: {len(json.dumps(output)):,} bytes")

# ── Summary ──
print("\n── SOURCE COVERAGE ──")
source_count = {"aa": 0, "livebench": 0, "arena": 0, "openllm": 0, "openrouter": 0}
multi_source = 0
for m in output_models:
    has_p = [s for s in m.get("pricing", {}) if m["pricing"][s]]
    has_b = [s for s in m.get("benchmarks", {}) if m["benchmarks"][s]]
    total = len(set(has_p + has_b))
    if total >= 2:
        multi_source += 1
    for s in has_b:
        source_count[s] = source_count.get(s, 0) + 1
    for s in has_p:
        if s not in source_count:
            source_count[s] = 0
        source_count[s] += 1

for s, c in sorted(source_count.items()):
    print(f"  {s:15s} {c} models")
print(f"\n  Models with 2+ sources: {multi_source}")

# Models with both AA benchmarks and another source
aa_plus = 0
for m in output_models:
    if "aa" in m.get("benchmarks", {}) and len([s for s in m.get("benchmarks", {}) if s != "aa"]) > 0:
        aa_plus += 1
    if "aa" in m.get("pricing", {}) and "openrouter" in m.get("pricing", {}):
        aa_plus += 1
print(f"  AA models with cross-source data: {aa_plus}")

print("\n── TOP 20 MODELS (by sources) ──")
def source_count_for_model(m):
    return len([s for s in m.get("pricing", {}) if m["pricing"][s]]) + len([s for s in m.get("benchmarks", {}) if m["benchmarks"][s]])

sorted_by_sources = sorted(output_models, key=source_count_for_model, reverse=True)
for m in sorted_by_sources[:20]:
    p = [s for s in m.get("pricing", {}) if m["pricing"][s]]
    b = [s for s in m.get("benchmarks", {}) if m["benchmarks"][s]]
    print(f"  {m['id']:40s} P:{','.join(p):25s} B:{','.join(b)}")
