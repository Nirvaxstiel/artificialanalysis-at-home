# LLM Provider Pricing Analysis

**Static dashboard for comparing LLM providers across IQ, cost, speed, verbosity, and cache efficiency.**

Built for users who want to pick a model and care about more than one axis.

## What it shows

85 reasoning models, 24 creators, 6 visualizations:

| Tab | What it answers |
|-----|-----------------|
| **01 Crossover** | X/Y scatter on any pair of (Intel, $/M, $/task, TOK, Speed). Bubble size = output tokens. |
| **02 Cost Breakdown** | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle. |
| **03 Provider Archetypes** | Radar per creator across 5 axes: IQ, Speed, Token Eff, Cache Eff, Cost Eff. |
| **04 Speed-Adjusted Cost** | Scatter: Speed × $/task, with sweet-spot quadrant. |
| **05 Cost per IQ Point** | Bar: how much $ you pay per IQ point, log scale. |
| **06 Data Table** | Sortable, filterable table of all fields. Click banner → jumps to this row. |

Top bar: filter by creator or reasoning intensity. Banner shows top-3 champions per metric — click to navigate.

## Why

Static, build-free, embeddable. No frameworks, no CDN, no bundlers — just HTML + JS + data.

## Stack

- **No build step.** No framework, no CDN, no bundler.
- **One HTML file** (`dashboard.html`) — embeddable anywhere that serves static files.
- **Vanilla JS** for charts. ~200 lines per viz, all 6 in `viz/`.
- **Inline data** — `window.PROCESSED_DATA` embedded directly in `dashboard.html`.

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Or just open `dashboard.html` directly in a modern browser.

## Data sources

| Source | What we get |
|--------|-------------|
| **Artificial Analysis** (primary) | IQ Index, $/M input/output/cache, speed, output tokens |
| **OpenRouter API** | Pricing for 49 models (cross-check) |
| **LiveBench** | Coding/agentic scores (17 models) |
| **Chatbot Arena** | Code Elo (18 models) |
| **OpenLLM** | Parameter counts (not yet integrated) |
| **Dirac.run** | Observed cache hit rates (configured in `_shared.js`) |

Data is current as of **6 July 2026**, AA Intelligence Index v4.1.

## Architecture

Shared config in `viz/_shared.js`:
- `CREATOR_COLORS` — 24 creators with distinct hex colors
- `SKU_PATTERNS` — slug-based splits (OSS / Mini / Nano / Flash / Code)
- `RADAR_AXES` — 5 radar axes (IQ / Speed / Token Eff / Cache Eff / Cost Eff)
- `FIELD_LABELS` — display names for table columns
- `COST_SEGMENTS` — color + label for cost breakdown
- `CACHE_HIT_RATES` — observed rates from external sources

Generic filter: `window.__legendFilter = { dim, val }` — shared across all views, top-bar driven.

See [ARCHITECTURE-REFERENCE.md](ARCHITECTURE-REFERENCE.md) for design decisions, scaling options, and trade-offs (gitignored temp doc).

## Layout

```
.
├── README.md
├── dashboard.html              ← the viz
├── LLM Provider Pricing Analysis.md  ← Obsidian note
├── ARCHITECTURE-REFERENCE.md   ← design doc (gitignored)
└── data/
    ├── processed.js           ← 85 models, primary dataset (loaded by dashboard)
    ├── aa_models_scraped.json  ← 99 AA-scraped models (raw)
    ├── model_registry.json     ← 2186 models, 6 sources
    ├── axes_catalog.json       ← 47 axes, typed
    ├── _build_*.py             ← pipeline scripts
    ├── _pull_sources.py        ← fetches LiveBench/Arena/OpenRouter
    ├── project_axes.py         ← ProjectionEngine (N-axis query)
    └── sources/
        ├── openrouter_models.json
        ├── livebench_*.csv
        ├── arena_*.json
        └── ...
└── viz/
    ├── _shared.js              ← legend filter, color maps, config
    ├── 01-crossover.js
    ├── 02-reasoning-tax.js
    ├── 03-provider-archetypes.js
    ├── 04-speed-cost.js
    ├── 05-cost-per-iq.js
    ├── 06-data-table.js
    └── README.md               ← viz worker contract
```

## License

Data: scraped from public web pages. Verify against AA before quoting.
Code: do whatever you want.

## Ingestion

Full pipeline to regenerate `data/processed.js` from fresh sources:

```bash
# 1. Pull latest benchmarks & pricing data
python data/_pull_sources.py

# 2. Merge all sources into unified registry
python data/_build_registry.py

# 3. Project selected axes → flat model rows for the dashboard
python data/_build_dashboard_data.py
```

**Pipeline order matters.**  
`_build_dashboard_data.py` reads `model_registry.json` (from step 2) and `processed.js` (from previous build, for AA bootstrap).  
Scraped AA data (`aa_models_scraped.json`) is pulled separately via the AA scraper — not part of this repo.

**What each step produces:**

| Step | Input(s) | Output | Models |
|------|----------|--------|--------|
| `_pull_sources` | OpenRouter API, OpenLLM parquet, LiveBench CSV | `data/sources/*` | N/A |
| `_build_registry` | `sources/*`, `aa_models_scraped.json` | `model_registry.json` | 2186 |
| `_build_dashboard_data` | `model_registry.json`, `processed.js` | `processed.js` | 38–85 |

**Coverage note:** The current `processed.js` (85 models, committed) is a snapshot from a prior AA scrape. When AA data is fresh, the pipeline produces ~38 models — the gap is slug mismatches between old and current AA scrapes, not a pipeline bug.

**To update the committed snapshot:** run the pipeline, verify `processed.js` has the expected models, then commit.

