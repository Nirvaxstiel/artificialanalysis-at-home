# LLM Provider Pricing Analysis

**Source:** Artificial Analysis — Intelligence Index v4.1 (6 Jul '26)
**Data:** 104 models, 24 creators in the rendered dashboard (2262 in the full registry, 8 sources)

## What it is

Static HTML dashboard at `dashboard.html`. Six viz tabs:

| Tab | What it shows |
|-----|---------------|
| 01 Crossover | X/Y scatter, any pair of IQ/$/M/$/task/TOK/Speed, **bubble size = context window** (OpenRouter `context_length`) |
| 02 Cost Breakdown | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle |
| 03 Provider Archetypes | Radar per creator: IQ / Speed / Token Eff / Cache Eff / Cost Eff |
| 04 Speed-Adjusted Cost | Speed × $/task scatter with sweet-spot quadrant |
| 05 Cost per IQ Point | $ per IQ point, log scale |
| 06 Data Table | Sortable, filterable. Click banner → jump to row |

## Files

- `dashboard.html` — the viz (single file, ~150KB with inline data)
- `data/processed.js` — 104 models, primary dataset (loaded by dashboard)
- `data/sources/aa/enriched/aa_model_data.json` — 99 AA scrapes (enriched)
- `data/sources/aa/aa_api_live.json` — 551 models, live AA API pull (release_date, creator, 16 eval scores)
- `data/sources/aa/aa_scrape_progress.json` — 99 slugs, image-chart scrape tracker
- `data/sources/aa/img/aa_img_models.json` — AA image-chart transcriptions (vision-benchmark scores)
- `data/sources/dirac/cache_hit_rates.json` — 276 rows, observed cache hit rates
- `data/model_registry.json` — 2262 models, 8 sources (serialized via `RegistryModel`)
- `data/axes_catalog.json` — 80 axes, typed
- `data/_build_*.py` — pipeline scripts
- `data/_domain/` — typed domain layer (`ProjectionRow`, `RegistryModel`, `RegistryModelMeta`)
- `viz/` — 6 viz scripts + shared config
- `README.md` — quick start, current state
- `ARCHITECTURE-REFERENCE.md` — design doc, trade-offs, gap audit (gitignored)
- `DATA-ACQUISITION.md` — **how each source is obtained** (scrape / API / vision / manual table) + repro steps

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| Artificial Analysis (primary, scraped) | 99 scrapes | IQ, $/M, speed, output tokens, params, cost segments |
| Artificial Analysis (live API) | 551 models | `release_date`, `creator`, 16 eval scores (HLE, GPQA, AIME'25, SciCode, LCR, TAU2, TerminalBench v2.1, etc.) — repurposed orphan enrichment |
| AA image charts | 99 models | Omniscience, Briefcase Elo (vision-transcribed) |
| OpenRouter API | 2262 models | Pricing, **context window** (`context_length`) |
| LiveBench | — | Coding/agentic/reasoning scores |
| Chatbot Arena (Code + Text) | — | Code/Text Elo |
| OpenLLM v2 | — | Params (B), IFEval, BBH, MATH-lvl5, GPQA, MMLU-Pro, MuSR |
| Dirac.run | 276 rows | Observed cache hit rates (Dirac.run + OpenRouter Effective Pricing) |

### Provenance rules
- **No cross-source price fallback.** AA and OpenRouter pricing are separate namespaces. A null in one is signal, not a gap to fill from the other.
- **Nulls preserved**, never dropped. Derived metrics computed only at transform time (`_build_dashboard_data.py`), never sourced-from-derived.
- **`confirmed_scraped`** flag (AA_IMG models) marks which speculative models the image scraper actually fetched — provenance, not data.

## Data additions since the initial build

- **Dirac cache hit rate** (`cache_hit_rate_max`, 11/104) — observed %, distinct from AA's cache *price*.
- **Live AA benchmarks** — 16 axes promoted from `aa_api_live.json` (`aa.hle`, `aa.gpqa`, `aa.lcr`, `aa.terminalbench_v2_1`, etc.). These are AA-sourced evals; where they overlap LiveBench axes (e.g. `gpqa`, `mmlu_pro`) they stay as a separate `aa.*` namespace — multi-source switchability is the feature.
- **`release_date`** (99/104) and **`creator`** (104/104, live data backfills static nulls) — from `aa_api_live.json`.
- **`context_window`** (104/104) — OpenRouter `context_length`, drives the crossover bubble size. Serialized through `RegistryModelMeta` (regression-guarded).
- **`RegistryModel` entity layer** — the previously-dead typed domain model is now the registry's validating serializer (`RegistryModel.from_flat`). Pipeline stores pricing/benchmarks as plain dicts; `RegistryModelMeta` types the `meta` block.

## Data gap audit

### Coverage (rendered 104-model set)
- **IQ**: 99/104
- **Pricing (inp+out)**: 104/104
- **Speed**: 103/104
- **Context window**: 104/104
- **Output tokens (`tokens_m`)**: 32/104 — verbosity metric, sparse
- **Cache hit rate (Dirac)**: 11/104
- **IQ per dollar**: 29/104
- **Live AA benchmarks**: 4–93/104 (sparse for older evals like AIME, MATH-500)
- **LiveBench / Arena**: partial

### Still open
- `cost_seg_*` (Input / Cached / Answer / Reasoning) — only on AA bar chart (color-coded, no labels)
- **Harness data** (codex, claude-code, aider) — not exposed by any source. Future axis: `metric × harness`

## Methodology

**AA Intelligence Index v4.1** — 9 weighted evals: GDPval-AA v2, τ³-Banking, Terminal-Bench v2.1, SciCode, HLE, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR.

**Cost per Task** = (input×input_price + cache_hit×cache_hit_price + cache_write×cache_write_price + reasoning×output_price + answer×output_price) / task_count, weighted by eval importance. Uses measured per-model per-eval token counts.

**Cache hit rate** is observed (Dirac.run, OpenRouter analytics) — AA only shows the cache *price* ($/M for cached tokens), not what % of input was actually cached. The radar `cache_eff` stays computed from AA's price discount only; Dirac's observed rate is a separate axis (`cache_hit_rate_max`), never conflated.

**Archetypes** (computed in `archetype` field): derive from intel tier × price tier.
- `frontier`: intel ≥ 55
- `premium`: intel ≥ 40, price > $3/M
- `sweet-spot`: intel ≥ 40, price ≤ $3/M
- `mid-tier`: intel 20-40
- `budget`: intel < 30, price ≤ $1/M
- `commodity`: intel < 20

## Key findings

- **DeepSeek + MiniMax dominate cost efficiency** — both have very high cache hit rates (~80%) plus low input prices
- **Anthropic + OpenAI** are at the top of IQ but cost ~10x more per IQ point
- **OSS models drag down creator averages** — splitting "OpenAI" and "OpenAI OSS" shows the real proprietary profile
- **Verbosity is the hidden cost** — DeepSeek V4 Pro emits 180M tokens per task, vs 89M for MiniMax-M3
- **Cache hit rate is the biggest cost lever** — 80% hit rate = 70% cost reduction on input
