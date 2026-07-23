# LLM Provider Pricing Analysis

**Source:** Artificial Analysis — Intelligence Index v4.1 (23 Jul '26)
**Data:** 120 models, 25 creators in the rendered dashboard (2276 in the full registry, 8 sources)

## What it is

Static HTML dashboard at `dashboard.html`. Five viz tabs:

| Tab | What it shows |
|-----|---------------|
| The Crossover | X/Y scatter, any pair of Intel / LiveBench / Arena Elo / OpenRouter pricing / speed / context. **Bubble size = context window** (OpenRouter `context_length`). |
| Cost Breakdown | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle. |
| Provider Archetypes | Radar per creator: IQ / Speed / Token Eff / Cache Eff / Cost Eff. |
| Cost per IQ Point | $ per IQ point, log scale. |
| Data Tables | Sortable, filterable (multi-column sort with shift+click). Click banner → jump to row. |

## Files

- `dashboard.html` — the viz (loads `data/processed.js` as `window.PROCESSED_DATA`)
- `data/processed.js` — 120 models, primary dataset (surfaced as `window.MODELS`)
- `data/model_registry.json` — 2276 models, 8 sources (serialized via `RegistryModel`)
- `data/axes_catalog.json` — typed axis catalog
- `data/_pipeline.py` — orchestrator: `build` / `build_from_cache` (offline) or full pull
- `data/_build_registry.py` — merges sources → `model_registry.json`
- `data/_build_axes.py` — → `axes_catalog.json`
- `data/_build_dashboard_data.py` — projects registry → `processed.js`
- `data/_domain/` — typed domain layer (`ProjectionRow`, `RegistryModel`)
- `data/sources/aa/` — `aa_models_scraped.json`, `aa_api_live.json` (579 models), `aa_charts_export.json`, `aa_jsonld_export.json`
- `data/sources/dirac/cache_hit_rates.json` — 398 rows, observed cache hit rates
- `viz/` — 5 viz scripts + `_result.js` / `_domain.js` / `_shared.js` / `_boot.js`
- `README.md` — quick start, current state, orchestrator modes
- `DATA-ACQUISITION.md` — **how each source is obtained** (scrape / API / vision / manual table) + repro steps

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| Artificial Analysis (primary, scraped) | 99 scrapes | IQ, $/M, speed, output tokens, params, cost segments |
| Artificial Analysis (live API) | 579 models | `release_date`, `creator`, 16 eval scores (HLE, GPQA, AIME'25, SciCode, LCR, TAU2, TerminalBench v2.1, etc.) |
| OpenRouter API | ~342 models | Pricing, **context window** (`context_length`) |
| LiveBench | 127 models | Coding/agentic/reasoning scores |
| Chatbot Arena (Code + Text) | 30 / 50 models | Code/Text Elo |
| OpenLLM v2 | 1783 models in subset | Params (B) |
| Dirac.run | 398 rows | Observed cache hit rates |

### Provenance rules

- **No cross-source price fallback.** AA and OpenRouter pricing are separate namespaces. A null in one is signal, not a gap to fill from the other.
- **Nulls preserved**, never dropped. Derived metrics computed only at transform time (`_build_dashboard_data.py`), never sourced-from-derived.

## Projection schema (rendered 120-model set)

Each `ProjectionRow` carries the fields listed in `viz/README.md`. Highlights:

- **Identity:** `slug`, `name`, `creator`, `type`, `release_date`, `archetype`, `pareto_optimal`
- **IQ / benchmarks:** `intel`, `iq_per_dollar_pt`, `iq_per_mtok`, `aa_*`, `omniscience_*`, `briefcase_*`, `agentic_index`, `coding_index`, `arena_code_*`, `arena_text_*`
- **Cost:** `cost_per_task`, `inp_price`, `out_price`, `cache_hit_price`, `openrouter_*_price_per_m`, `iq_per_1k_pt`, `cost_per_iq_pt`, `useful_cost`, `reasoning_tax_pct`, `cost_percentile`, `iq_percentile`
- **Speed / verbosity:** `speed_tps`, `ttft`, `tokens_m`, `context_window`
- **Radar (precomputed):** `radar_intel`, `radar_speed`, `radar_cache_eff`, `radar_cost_eff`, `radar_ctx`
- **Cost Breakdown** segments are computed at render time from `cost_seg_*` on the source model when `has_breakdown` is true; they are not stored on the projection row.

## Methodology

**AA Intelligence Index v4.1** — weighted evals (GDPval-AA v2, Banking, Terminal-Bench v2.1, SciCode, HLE, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR).

**Cost per Task** = (input×input_price + cache_hit×cache_hit_price + cache_write×cache_write_price + reasoning×output_price + answer×output_price) / task_count, weighted by eval importance. Uses measured per-model per-eval token counts.

**Cache hit rate** is observed (Dirac.run, OpenRouter analytics) — AA only shows the cache *price* ($/M for cached tokens), not what % of input was actually cached. The radar `cache_eff` is computed from AA's price discount only; Dirac's observed rate is a separate axis (`cache_hit_rate_max`), never conflated.

**Archetypes** (computed in `archetype` field): derive from intel tier × price tier.
- `frontier`: intel ≥ 55
- `premium`: intel ≥ 40, price > $3/M
- `sweet-spot`: intel ≥ 40, price ≤ $3/M
- `mid-tier`: intel 20–40
- `budget`: intel < 30, price ≤ $1/M
- `commodity`: intel < 20

## Key findings

- **DeepSeek + MiniMax dominate cost efficiency** — both have very high cache hit rates (~80%) plus low input prices
- **Anthropic + OpenAI** are at the top of IQ but cost ~10x more per IQ point
- **OSS models drag down creator averages** — splitting "OpenAI" and "OpenAI OSS" shows the real proprietary profile
- **Verbosity is the hidden cost** — DeepSeek V4 Pro emits 180M tokens per task, vs 89M for MiniMax-M3
- **Cache hit rate is the biggest cost lever** — 80% hit rate = 70% cost reduction on input
