# LLM Provider Pricing Analysis

**Static dashboard for comparing LLM providers across IQ, cost, speed, verbosity, and cache efficiency.**

Built for users who want to pick a model and care about more than one axis.

## What it shows

117 models (rendered), 2275 in the registry, 24 creators, 5 visualizations:

| Tab | What it answers |
|-----|-----------------|
| **The Crossover** | X/Y scatter on any pair of (Intel, LiveBench, Arena Elo, OpenRouter pricing, speed, context). Bubble size = context window. |
| **Cost Breakdown** | Per-model cost split (Input / Cached / Answer / Reasoning) with cache hit rate toggle. |
| **Provider Archetypes** | Radar per creator across 5 axes: IQ, Speed, Token Eff, Cache Eff, Cost Eff. |
| **Cost per IQ Point** | Bar: how much $ you pay per IQ point, log scale. |
| **Data Tables** | Sortable, filterable multi-view table of all fields. Click banner → jumps to this row. |

Top bar: filter by creator or reasoning intensity. Banner shows top-3 champions per metric — click to navigate.

## Why

Static, build-free to serve, embeddable. No frameworks, no CDN, no bundlers — just HTML + JS + data.

## Stack

- **No build step.** No framework, no CDN, no bundler.
- **One HTML file** (`dashboard.html`) — embeddable anywhere that serves static files.
- **Vanilla JS** for charts, all 5 in `viz/`.
- **External data** — `window.PROCESSED_DATA` loaded from `data/processed.js` (a generated `window.PROCESSED_DATA = {...}` script). The dashboard does not embed data inline.

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Or just open `dashboard.html` directly in a modern browser (it loads `processed.js` via a `<script src>`).

## Data sources

| Source | What we get |
|--------|-------------|
| **Artificial Analysis** (primary) | Intelligence Index, $/M input/output/cache, speed, output tokens, cost segments, 16 eval scores |
| **OpenRouter API** | Pricing + context window for ~345 models (cross-check / context) |
| **LiveBench** | Coding/agentic/reasoning scores (127 models) |
| **Chatbot Arena** | Code + Text Elo (30 / 50 models) |
| **OpenLLM v2** | Parameter counts (1783 models in subset) |
| **Dirac.run** | Observed cache hit rates |

Data is current as of **11 July 2026**, AA Intelligence Index v4.

## Architecture

### Build pipeline (`data/`)
Each stage returns a `Result` (Ok/Err). The shared `Pipeline` class (`data/_pipeline.py`) threads a `ctx` dict and short-circuits at the first `Err` instead of raising. Stages compose their steps with `Pipeline(...).then(name, fn).then(...).run()`.

Entry point: `python -m data._pipeline`.

| Command | Mode | What it does |
|---------|------|--------------|
| `python -m data._pipeline build` | **offline** | `build_from_cache`: registry → axes → dashboard, reading committed `data/sources/*`. No network. |
| `python -m data._pipeline build_from_cache` | **offline** | same as `build` (alias). |
| `python -m data._pipeline` (no arg) or any other arg | **full pull** | `build()`: runs `_pull_sources` first (network), then builds. |

> `build` / `build_from_cache` never touch the network. Only the full build (`build()`) pulls. This separation is deliberate — committed source files are the build inputs, so a refresh is an explicit, deliberate act.

Stages (each a `Result`-returning `run()`/`build()`):

| Stage | Inputs | Output | Models |
|-------|--------|--------|--------|
| `_pull_sources` | OpenRouter API, OpenLLM parquet, LiveBench CSV | `data/sources/*` | (writes caches) |
| `_build_registry` | `sources/*` (aa raw+enriched+live, openrouter, dirac, livebench, arena, openllm) | `model_registry.json` | 2275 |
| `_build_axes` | `model_registry.json` | `axes_catalog.json` | — |
| `_build_dashboard_data` | `model_registry.json` | `processed.js` | 117 |

`_build_registry.run()` merges sources into a unified registry: `step_aa`, `step_aa_img`, `step_scrape_progress`, `step_dirac`, `step_livebench`, `step_arena_text`, `step_arena_code`, `step_openllm`, `step_openrouter`, `step_misc`, `step_name_map`, `step_write` — each a `Result` step over shared `ctx`, short-circuiting on the first `Err`.

Serialized via the typed domain layer in `data/_domain/` (`RegistryModel`, `ProjectionRow`).

### Viz layer (`viz/`)
JS uses the same `Result`/`Pipeline` idiom. `viz/_result.js` defines `ok`/`err`/`fromFn`/`Pipeline` (mirrors `data/_pipeline.Pipeline`). `_boot.js` orchestrates load via `window.Result.Pipeline({}).then(bootstrap_models).then(build_shell)...run()` — identical shape to the Python stages. Each viz file is self-contained, registering itself in `window.VIZ_REGISTRY`.

Shared config in `viz/_shared.js`:
- `CREATOR_COLORS` — 24 creators with distinct hex colors
- `SKU_PATTERNS` — slug-based splits (OSS / Mini / Nano / Flash / Code)
- `RADAR_AXES` — 5 radar axes (IQ / Speed / Token Eff / Cache Eff / Cost Eff)
- `FIELD_LABELS` — display names for table columns
- `COST_SEGMENTS` — color + label for cost breakdown
- `CACHE_HIT_RATES` — observed rates from Dirac.run / OpenRouter

Generic filter: `window.__legendFilter = { dim, val }` — shared across all views, top-bar driven.

> See `viz/README.md` for the viz worker contract.

## Layout

```
.
├── README.md
├── dashboard.html              ← the viz (loads data/processed.js)
├── data/
│   ├── processed.js           ← 117 models, primary dataset (loaded by dashboard)
│   ├── model_registry.json     ← 2277 models, 8 sources (serialized via RegistryModel)
│   ├── axes_catalog.json       ← typed axis catalog
│   ├── _pipeline.py            ← orchestrator: build / build_from_cache / build() (pull)
│   ├── _pull_sources.py        ← fetches LiveBench / OpenLLM / OpenRouter
│   ├── _build_registry.py      ← merges sources → model_registry.json
│   ├── _build_axes.py          ← axes_catalog.json
│   ├── _build_dashboard_data.py← projects registry → processed.js
│   ├── _domain/                ← typed domain layer (ProjectionRow, RegistryModel)
│   ├── project_axes.py         ← ProjectionEngine (N-axis query)
│   ├── sources/                ← all source data + per-source build modules
│   └── _result.py              ← Result/Either monad (Python)
└── viz/
    ├── _result.js              ← Result + Pipeline (JS)
    ├── _domain.js              ← ProjectionRow load boundary (JS)
    ├── _shared.js              ← legend filter, color maps, config
    ├── _boot.js                ← boot orchestration pipeline
    ├── crossover.js            ← tab: The Crossover
    ├── cost-breakdown.js       ← tab: Cost Breakdown
    ├── provider-archetypes.js  ← tab: Provider Archetypes
    ├── cost-per-iq.js          ← tab: Cost per IQ Point
    ├── data-table.js           ← tab: Data Tables
    └── README.md               ← viz worker contract
```

## License

Data: scraped from public web pages. Verify against AA before quoting.
Code: do whatever you want.

## Build / refresh

```bash
# Offline (no network) — rebuild from committed sources:
python -m data._pipeline build            # or: build_from_cache

# Full refresh (network pull of OpenRouter/LiveBench/OpenLLM, then build):
python -m data._pipeline                  # no arg → build() pulls + builds
```

`_pull_sources.py` covers only 3 of 8 sources (OpenRouter API, LiveBench CSV, OpenLLM v2 parquet). The other five — AA scraped, AA live API, AA image charts, Dirac.run, Chatbot Arena — are acquired **manually** (scrape / API curl / vision-transcription / table-copy / JSON download) and committed as files. See `DATA-ACQUISITION.md` for the full per-source method, auth, and repro steps.

**Build order matters.** `_build_registry.py` reads AA data from `data/sources/aa/` — never from pipeline output. No circular dependency.

**To update the committed snapshot:** run a full build (`python -m data._pipeline`), verify `processed.js` has the expected models, then commit.
