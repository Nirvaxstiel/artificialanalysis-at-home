# LLM Provider Pricing Analysis

**Static dashboard for comparing AA indexes, cost, speed, benchmarks, and cache efficiency.**

The dashboard compares models on more than one axis at a time.

## What it shows

41 models across 18 creators from AA's current exports; 5 visualizations:

| Tab | What it answers |
|-----|-----------------|
| **The Crossover** | X/Y scatter on any pair of (Intel, LiveBench, Arena Elo, OpenRouter pricing, speed, context). Bubble size = context window. |
| **Cost Breakdown** | Per-model cost split (Input / Cached / Answer / Reasoning) on the AA baseline, or repriced on any cache provider's observed effective rates. |
| **Provider Archetypes** | Radar per AA family, grouped under its creator, across IQ, Speed, Cache Eff, Cost Eff, and Context. |
| **Cost per IQ Point** | Bar: how much $ you pay per IQ point, log scale. |
| **Data Tables** | Sortable, filterable multi-view table of all fields. Click banner → jumps to this row. |

Top bar: filter by creator or reasoning intensity. Banner shows top-3 champions per metric — click to navigate.

## Why

Static, build-free to serve, embeddable. No frameworks, no CDN, no bundlers — just HTML + JS + data.

## Stack

- **No frontend build step.** The browser needs no framework, no CDN, and no bundler.
- **One HTML file** (`dashboard.html`) — embeddable anywhere that serves static files.
- **Vanilla JS** for charts, all 5 in `viz/`.
- **External data** — `window.PROCESSED_DATA` loaded from `data/processed.js` (a generated `window.PROCESSED_DATA = {...}` script). The dashboard does not embed data inline.

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Or just open `dashboard.html` directly in a modern browser (it loads `processed.js` via a `<script src>`).

The Python pipeline in `data/` is a separate build. It generates the data files. It is not part of the frontend runtime.

## Data sources

| Source | What we get |
|--------|-------------|
| **Artificial Analysis** (primary) | Intelligence Index, Finance & Accounting, AnalystAgent pass rate, Briefcase Elo, GDPval-AA Elo, Omniscience, time/task, pricing, speed |
| **OpenRouter API** | Pricing + context window for ~10 models (cross-check / context) |
| **LiveBench** | Coding/agentic/reasoning scores (5 models) |
| **Chatbot Arena** | Code + Text Elo (2 / 4 models) |
| **OpenLLM v2** | Parameter counts (0 models in subset) |
| **Dirac.run** | Observed cache hit rates + effective $/M per provider (auto-pulled) |

AA export snapshot: **10 Sep 2026**. The build generates the per-source dates and in-scope counts into `data/processed.js` meta (`sources_meta`). The dashboard footer shows them.

## Architecture

### Build pipeline (`data/`)
Each stage returns a `Result` (Ok/Err). The shared `Pipeline` class (`data/_pipeline.py`) threads a `ctx` dict and stops at the first `Err`. It does not raise. Stages compose their steps with `Pipeline(...).then(name, fn).then(...).run()`.

Entry point: `python -m data._pipeline`.

| Command | Mode | What it does |
|---------|------|--------------|
| `python -m data._pipeline build` | **offline** | `build_from_cache`: registry → axes → dashboard, reading committed `data/sources/*`. No network. |
| `python -m data._pipeline build_from_cache` | **offline** | same as `build` (alias). |
| `python -m data._pipeline` (no arg) or any other arg | **full pull** | `build()`: runs `_pull_sources` first (network), then builds. |

> `build` / `build_from_cache` never touch the network. Only the full build (`build()`) pulls. This separation is deliberate. The committed source files are the build inputs. A refresh is an explicit act.

Stages (each a `Result`-returning `run()`/`build()`):

| Stage | Inputs | Output | Models |
|-------|--------|--------|--------|
| `_pull_sources` | OpenRouter API, OpenLLM parquet, LiveBench CSV, Dirac.run table | `data/sources/*` | (writes caches) |
| `_build_registry` | `sources/*` (AA charts, JSON-LD and live metadata; supplementary sources scoped to AA exports) | `model_registry.json` | 41 |
| `_build_axes` | `model_registry.json` | `axes_catalog.json` | — |
| `_build_dashboard_data` | `model_registry.json` | `processed.js` | 41 |

`_build_registry.run()` seeds models from AA's current chart and JSON-LD exports. It then enriches only those models, from metadata and supplementary sources.

The typed domain layer in `data/_domain/` (`RegistryModel`, `ProjectionRow`) serializes the data.

### Viz layer (`viz/`)
The JavaScript layer uses the same `Result`/`Pipeline` idiom. `viz/_result.js` defines `ok`/`err`/`fromFn`/`Pipeline`, and mirrors `data/_pipeline.Pipeline`. `_boot.js` loads the data with `window.Result.Pipeline({}).then(bootstrap_models).then(build_shell)...run()`. The shape is identical to the Python stages. Each viz file is self-contained and registers itself in `window.VIZ_REGISTRY`.

Shared config in `viz/_shared.js`:
- `CREATOR_COLORS` — curated colors for current creators
- `RADAR_AXES` — 5 radar axes (IQ / Speed / Cache Eff / Cost Eff / Context)
- `FIELD_LABELS` — display names for table columns
- `COST_SEGMENTS` — color + label for cost breakdown
- `dirac_cache_hit_rates` (per model) — observed cache hit % + effective $/M per provider, from Dirac.run / OpenRouter effective pricing. This config drives the Cost Breakdown provider mode and the Provider Data view

Provider Archetypes groups models by creator and the sourced AA family (`release.slug` / `release.name`) in `processed.js`.

Generic filter: `window.__legendFilter = { dim, val }` — shared across all views, top-bar driven.

> See `viz/README.md` for the viz worker contract.

## Layout

```
.
├── README.md
├── dashboard.html              ← the viz (loads data/processed.js)
├── data/
│   ├── processed.js           ← 41 models, primary dataset (loaded by dashboard)
│   ├── model_registry.json     ← 41 models, 7 sources (serialized via RegistryModel)
│   ├── axes_catalog.json       ← typed axis catalog
│   ├── _pipeline.py            ← orchestrator: build / build_from_cache / build() (pull)
│   ├── _pull_sources.py        ← fetches LiveBench / OpenLLM / OpenRouter / Dirac.run
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

# Full refresh (network pull of OpenRouter/LiveBench/OpenLLM/Dirac.run, then build):
python -m data._pipeline                  # no arg → build() pulls + builds
```

`_pull_sources.py` covers 4 of 7 sources: the OpenRouter API, the LiveBench CSV, the OpenLLM v2 parquet, and the Dirac.run HTML table. The other sources are AA (scraped pages, SVG and JSON-LD console exports, live API) and Chatbot Arena. Acquire those **manually** (scrape / console query / API curl / JSON download) and commit them as files. See `DATA-ACQUISITION.md` for the per-source method, the auth, and the repro steps.

**Build order matters.** `_build_registry.py` reads AA data from `data/sources/aa/`. It never reads pipeline output, so there is no circular dependency.

**To update the committed snapshot:** run a full build (`python -m data._pipeline`). Make sure that `processed.js` has the expected models. Then commit.
