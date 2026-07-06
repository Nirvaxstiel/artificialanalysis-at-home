# LLM Provider Pricing Analysis

**Source:** Artificial Analysis — Intelligence Index v4.1 (6 Jul '26)
**Data:** 85 models, 24 creators — reasoning models only

## What it is

Static HTML dashboard at `dashboard.html`. Six viz tabs:

| Tab | What it shows |
|-----|---------------|
| 01 Crossover | X/Y scatter, any pair of IQ/$/M/$/task/TOK/Speed, bubble = output tokens |
| 02 Cost Breakdown | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle |
| 03 Provider Archetypes | Radar per creator: IQ / Speed / Token Eff / Cache Eff / Cost Eff |
| 04 Speed-Adjusted Cost | Speed × $/task scatter with sweet-spot quadrant |
| 05 Cost per IQ Point | $ per IQ point, log scale |
| 06 Data Table | Sortable, filterable. Click banner → jump to row |

## Files

- `dashboard.html` — the viz (single file, ~150KB with inline data)
- `data/processed.json` — 85 models, primary dataset
- `data/aa_models_scraped.json` — 99 raw AA scrapes
- `data/model_registry.json` — 2186 models, 6 sources
- `data/axes_catalog.json` — 47 axes, typed
- `data/_build_*.py` — pipeline scripts
- `viz/` — 6 viz scripts + shared config
- `README.md` — quick start, current state
- `ARCHITECTURE-REFERENCE.md` — design doc, trade-offs, gap audit (gitignored)

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| Artificial Analysis (primary) | 99 scrapes | IQ, $/M, speed, output tokens, params, cost segments |
| OpenRouter API | 49/85 | Pricing fallback for models without AA pricing |
| LiveBench | 23/85 | Coding/agentic scores |
| Chatbot Arena | 18/85 | Code Elo |
| Dirac.run / OpenRouter (manual) | 30 in `CACHE_HIT_RATES` | Observed cache hit rates |
| Old data (pre-AA batch) | 18 models | Historical cost_per_task, archetypes, LiveBench |

## Data gap audit (6 July 2026)

### Coverage
- **IQ**: 98% (2 models missing: gpt-5-5-instant-06-26, gpt-5-5-pro)
- **Pricing (inp+out)**: 64% (31 models missing)
- **Speed**: 74%
- **Tokens (output M)**: 35% — only old data + some AA
- **Cost per task**: 31% — only old data
- **LiveBench / Arena**: 27% / 21%

### Easy wins (deferred, see ARCHITECTURE-REFERENCE)

1. **Fallback pricing**: 11 of 31 unpriced models have OpenRouter data → use as `inp_price`/`out_price` fallback
2. **Re-scrape AA pages**: extract more `tokens_m` and `params_b` from page text
3. **Re-run `_pull_sources.py`**: refresh LiveBench/Arena
4. **Pure derivations**: `iq_per_mtok`, `iq_per_1k_pt`, `cost_per_iq_pt`, `reasoning_tax_pct` (all just division)

### Hard problems (no public API)

- `cost_seg_*` (Input / Cached / Answer / Reasoning) for new models — only on AA bar chart (color-coded, no labels)
- Observed cache hit rates — no public analytics API

## Methodology

**AA Intelligence Index v4.1** — 9 weighted evals: GDPval-AA v2, τ³-Banking, Terminal-Bench v2.1, SciCode, HLE, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR.

**Cost per Task** = (input×input_price + cache_hit×cache_hit_price + cache_write×cache_write_price + reasoning×output_price + answer×output_price) / task_count, weighted by eval importance. Uses measured per-model per-eval token counts.

**Cache hit rate** is observed (Dirac.run, OpenRouter analytics) — AA only shows the cache *price* ($/M for cached tokens), not what % of input was actually cached.

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
