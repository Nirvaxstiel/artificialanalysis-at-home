# LLM Provider Pricing Analysis

**Source:** Artificial Analysis — Intelligence Index v4.3 (AA snapshot 10 Sep '26)
**Data:** 41 AA-covered models across 18 creators. Supplementary sources enrich this export-defined set only. Per-source dates and counts are in `data/processed.js` meta (`sources_meta`).

## What it is

Static HTML dashboard at `dashboard.html`. Five viz tabs:

| Tab | What it shows |
|-----|---------------|
| The Crossover | X/Y scatter, any pair of Intel / LiveBench / Arena Elo / OpenRouter pricing / speed / context. **Bubble size = context window** (OpenRouter `context_length`). |
| Cost Breakdown | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle. |
| Provider Archetypes | Radar per creator: IQ / Speed / Cache Eff / Cost Eff / Context. |
| Cost per IQ Point | $ per IQ point, log scale. |
| Data Tables | Sortable, filterable (multi-column sort with shift+click). Click banner → jump to row. |

## Files

- `dashboard.html` — the viz (loads `data/processed.js` as `window.PROCESSED_DATA`)
- `data/processed.js` — 41 models, primary dataset (surfaced as `window.MODELS`)
- `data/model_registry.json` — 41 models, 7 sources (serialized via `RegistryModel`)
- `data/axes_catalog.json` — typed axis catalog
- `data/_pipeline.py` — orchestrator: `build` / `build_from_cache` (offline) or full pull
- `data/_build_registry.py` — merges sources → `model_registry.json`
- `data/_build_axes.py` — → `axes_catalog.json`
- `data/_build_dashboard_data.py` — projects registry → `processed.js`
- `data/_domain/` — typed domain layer (`ProjectionRow`, `RegistryModel`)
- `data/sources/aa/` — AA chart and JSON-LD exports. The cached live API supplies creator and release metadata
- `data/sources/dirac/cache_hit_rates.json` — 398 rows, observed cache hit rates
- `viz/` — 5 viz scripts + `_result.js` / `_domain.js` / `_shared.js` / `_boot.js`
- `README.md` — quick start, current state, orchestrator modes
- `DATA-ACQUISITION.md` — **how each source is obtained** (scrape / API / vision / manual table) + repro steps

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| Artificial Analysis exports | 41 in-scope models | Intelligence, Finance & Accounting, AnalystAgent pass rate, Briefcase Elo, GDPval-AA Elo, Omniscience, time/task, pricing, speed |
| Artificial Analysis live API cache | scoped to AA exports | `release_date` and creator metadata |
| OpenRouter API | 10 in-scope models | Pricing, **context window** (`context_length`) |
| LiveBench | 5 in-scope models | Coding/agentic/reasoning scores |
| Chatbot Arena (Code + Text) | 4 / 2 in-scope models | Code/Text Elo |
| OpenLLM v2 | 0 in-scope models | Params (B) |
| Dirac.run | 6 in-scope models | Observed cache hit rates |

### Provenance rules

- **No cross-source price fallback.** AA and OpenRouter pricing are separate namespaces. A null in one is signal, not a gap to fill from the other.
- **Nulls are preserved**, never dropped. The build computes derived metrics only at transform time (`_build_dashboard_data.py`), and never from a derived value.

## Projection schema (41-model set)

Each `ProjectionRow` carries the fields listed in `viz/README.md`. Highlights:

- **Identity:** `slug`, `name`, `creator`, `type`, `release_date`, `archetype`, `pareto_optimal`
- **AA indexes:** `intel`, `aa_finance_accounting_index`, `aa_analyst_agent_pass_5`, `aa_briefcase_elo`, `aa_gdpval_elo`, `aa_omniscience_index`
- **Cost:** `cost_per_task`, `inp_price`, `out_price`, `cache_hit_price`, `openrouter_*_price_per_m`, `reasoning_tax_pct`
- **Speed / context:** `speed_tps`, `aa_time_per_task`, `context_window`
- **Radar (precomputed):** `radar_intel`, `radar_speed`, `radar_cache_eff`, `radar_cost_eff`, `radar_ctx`
- **Derived value:** the build calculates cost per IQ point from sourced `cost_per_task` and `intel` for the chart and the table. It is not stored in `processed.js`.
- **Provenance:** each populated field is tagged `sourced` or `derived`.
- **Cost Breakdown** reads source `cost_seg_*` values when `has_breakdown` is true.

## Methodology

AA index and benchmark values come from the current chart and JSON-LD exports. The live API cache supplements creator and release metadata. It does not define model scope.

**Cost per Task** is sourced from the AA per-task dataset. Full-index “Cost to Run” values are separate and are not used as per-task prices.

**Cache hit rate** is observed (Dirac.run, OpenRouter analytics). AA shows only the cache *price* ($/M for cached tokens), not the percentage of input that was actually cached. The build computes the radar `cache_eff` from the AA price discount only. The Dirac observed rate is a separate axis (`cache_hit_rate_max`), and the two are never conflated.

**Archetypes** (computed in `archetype` field, first match wins): derive from intel tier × cost × speed × params.
- `frontier`: intel ≥ 50
- `reasoning`: reasoning_tax_pct ≥ 20
- `cheap`: cost_per_task < $0.50 and intel ≥ 30
- `fast`: speed_tps ≥ 150
- `compact`: params < 30B and intel ≥ 30
- `uncategorized`: none of the above (most non-AA models — they carry no intel)
