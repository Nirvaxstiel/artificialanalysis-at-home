# Viz Worker Contract

Each viz is a self-contained JS file in this directory. The dashboard shell (`dashboard.html`) loads all of them and uses `window.VIZ_REGISTRY` to switch views.

## File template

```js
// viz/slug.js
(function () {
  function render(container, data) {
    // data = window.MODELS (array of ProjectionRow, see below)
    // container = DOM element to mount into
    // ... build your SVG/HTML ...
  }

  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'slug',
    name: 'Human Title',
    subtitle: 'One-line description',
    render
  });
})();
```

Note: files are named by slug (`crossover.js`, `cost-breakdown.js`, …), **not** `NN-slug.js`.

## Rules

1. **Read-only inputs.** `data/processed.js` (loaded as `window.PROCESSED_DATA`, surfaced as `window.MODELS`) is the only data source. Do not write to it.
2. **Self-contained styles.** Inline `<style>` in your container, or use the CSS custom properties from `dashboard.html` (`--neon`, `--neon2`, `--bg`, `--fg`, `--muted`, `--border`).
3. **Reuse the tooltip.** If you have hoverable elements, attach to the shared `#tooltip` div from `dashboard.html` using the `buildTooltip(model)` function (also exposed globally).
4. **No external dependencies.** No CDN, no fetch, no imports. Pure DOM + SVG.
5. **Match the brutalist aesthetic.** Hard borders, monospace, neon accents, `//` comments.
6. **No hardcoded values.** Use `window.FIELD_LABELS`, `window.RADAR_AXES`, and `window.COST_SEGMENTS` from `_shared.js`. Provider Archetypes reads official `model.family` data from `processed.js`.
7. **Use the legend filter.** Read `window.__legendFilter` to dim non-matching elements.

## Boot orchestration

`viz/_boot.js` runs the boot sequence as a `Pipeline` (mirrors `data/_pipeline.Pipeline`):

`bootstrap_models → validate_schema → header_meta → source_freshness → build_shell → render_legend → render_first → wire_tabs → wire_filter_sync → banner_stats → pareto_count → banner_nav → repo_links`

Each step is a named `Result`-returning function over a shared `ctx`. `render()` internals in each viz file are untouched. The load boundary (`viz/_domain.js`) wraps `processed.js` parsing in `Result`. A parse failure short-circuits boot with `ctx._failed_step` set.

## Available data (from `window.MODELS`)

Each model is a `ProjectionRow` with these fields (41 models, and all 41 carry AA data):

| Field | Type | Notes |
|-------|------|-------|
| `slug` | string | URL identifier (hyphenated) |
| `name` | string | Display name |
| `creator` | string | Model creator org; can be absent |
| `type` | string | Model type |
| `intel` | float | AA Intelligence Index |
| `aa_finance_accounting_index` | float | Finance & Accounting score (0–100) |
| `aa_analyst_agent_pass_5` | float | AnalystAgent pass⁵ rate (0–1) |
| `aa_briefcase_elo` / `aa_gdpval_elo` | float | AA-Briefcase / GDPval-AA Elo |
| `aa_omniscience_index` | float | Omniscience Index (−100–100) |
| `aa_time_per_task` | float | Seconds per Intelligence Index task |
| `cost_per_task` | float | AA-sourced USD per task |
| `inp_price` / `out_price` / `cache_hit_price` | float | AA $/M input, output, and cached input tokens |
| `cost_seg_*` | float | AA per-task cost components for Cost Breakdown |
| `speed_tps` | float | Output tokens per second |
| `openrouter_*_price_per_m` | float | OpenRouter pricing |
| `openrouter_vendor` | string | OpenRouter vendor tag |
| `context_window` | int | OpenRouter context length; drives the crossover bubble size |
| `arena_code_*` / `arena_text_*` | float | Chatbot Arena Code / Text results |
| `livebench_*` / `openllm_*` | float | Supplementary benchmark results when in scope |
| `params_b` / `co2_kg` | float | Supplementary metadata when available |
| `cache_hit_rate_max` / `dirac_cache_hit_rates` | float / array | Dirac observed rate and provider-grouped rates |
| `reasoning_tax_pct` | float | Derived from sourced reasoning and total task cost |
| `radar_*` | float | Normalized Provider Archetypes values |
| `archetype` / `pareto_optimal` / `has_breakdown` | string / bool | Derived categorization, frontier, and cost-data presence |
| `blended` | float | Derived AA blended $/M (3:1 input:output) |
| `release_date` | string | AA live API metadata |
| `provenance` | object | Per-field `sourced` / `derived` tags |

The build calculates cost per IQ point from sourced `cost_per_task` and `intel` for the chart and the table. It is not stored in `processed.js`. Full-index “Cost to Run” values are not used as per-task prices.

## Shared config (`_shared.js`)

- `window.CREATOR_COLORS` — curated creator → hex color map
- `window.VIZ_REGISTRY` — array of `{id, name, subtitle, render}`
- `window.__legendFilter` — global filter state `{ dim, val } | null`
- `window.__setLegendFilter(dim, val)` — toggle helper
- `window.__modelOpacity(m)` — returns 0–1 for fade effect based on filter
- `window.__filterSubscribers` — `Set` of callbacks invoked on filter change
- `window.__renderCreatorLegend()` — generates HTML legend strip
- `model.family` — official AA release slug and name used to group Provider Archetypes
- `window.RADAR_AXES` — 5 radar axes (IQ, speed, cache efficiency, cost efficiency, context)
- `window.COST_SEGMENTS` — color + label for cost breakdown
- `window.FIELD_LABELS` — display names for table columns
- `model.dirac_cache_hit_rates` — observed cache hit % + effective $/M per provider (Dirac.run / OpenRouter effective pricing)

## Shell globals (defined in dashboard.html)

- `buildTooltip(model)` — full data tooltip builder
- `attachTooltip(el, model)` — convenience: attaches mouseenter/move/leave
- `window.PROCESSED_DATA` — the raw generated dataset object (`{meta, sources, sources_meta, models}`); `meta.counts` = `{models, aa_models, creators}`, `meta.sources_meta` = per-source `{models, as_of, note?}`
- `window.MODELS` — array of all models (41), after the `_domain.js` load boundary

## Current viz files

- `_result.js` — `Result` (`ok`/`err`/`fromFn`) + `Pipeline` (JS port of `data/_pipeline.Pipeline`)
- `_domain.js` — `ProjectionRow.load` boundary, and it populates `window.MODELS`
- `_shared.js` — shared state, config, tooltip wiring
- `_boot.js` — boot orchestration pipeline
- `crossover.js` — scatter with x/y axis dropdowns, bubble size = context window
- `cost-breakdown.js` — stacked bars on the AA baseline, or repriced per cache provider (scaled $/task + effective-rate block)
- `provider-archetypes.js` — radar charts per creator
- `cost-per-iq.js` — cost per IQ point bar chart
- `data-table.js` — sortable, filterable six-view table (AA Indexes, multi-column sort with shift+click)

## Testing locally

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Black-box JS tests (`tests/test_*_js.js`) load `data/processed.js` under Node with a DOM stub, and they assert pure-transform behavior. No jsdom. Stub at the boundary.
