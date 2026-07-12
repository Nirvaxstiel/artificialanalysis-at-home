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

1. **Read-only inputs.** `data/processed.js` (loaded as `window.PROCESSED_DATA`, surfaced as `window.MODELS`) is the only data source. Don't write to it.
2. **Self-contained styles.** Inline `<style>` in your container, or use the CSS custom properties from `dashboard.html` (`--neon`, `--neon2`, `--bg`, `--fg`, `--muted`, `--border`).
3. **Reuse the tooltip.** If you have hoverable elements, attach to the shared `#tooltip` div from `dashboard.html` using the `buildTooltip(model)` function (also exposed globally).
4. **No external dependencies.** No CDN, no fetch, no imports. Pure DOM + SVG.
5. **Match the brutalist aesthetic.** Hard borders, monospace, neon accents, `//` comments.
6. **No hardcoded values.** Use `window.FIELD_LABELS`, `window.RADAR_AXES`, `window.SKU_PATTERNS`, `window.COST_SEGMENTS` from `_shared.js`.
7. **Use the legend filter.** Read `window.__legendFilter` to dim non-matching elements.

## Boot orchestration

`viz/_boot.js` runs the boot sequence as a `Pipeline` (mirrors `data/_pipeline.Pipeline`):

`bootstrap_models → header_meta → build_shell → render_first → wire_tabs → wire_filter_sync → banner_stats → pareto_count → banner_nav → repo_links`

Each step is a named `Result`-returning function over a shared `ctx`. `render()` internals in each viz file are untouched. The load boundary (`viz/_domain.js`) wraps `processed.js` parsing in `Result`; a parse failure short-circuits boot with `ctx._failed_step` set.

## Available data (from `window.MODELS`)

Each model is a `ProjectionRow` with these fields (117 models total):

| Field | Type | Notes |
|-------|------|-------|
| `slug` | string | URL identifier (hyphenated) |
| `name` | string | Display name (may include effort qualifiers) |
| `creator` | string | Model creator org |
| `type` | string | "Proprietary" or "Open weights" |
| `intel` | float | AA Intelligence Index v4 |
| `cost_per_task` | float | USD per task (AA-derived) |
| `iq_per_dollar_pt` | float | IQ per $ (point-normalized) |
| `iq_per_mtok` / `iq_per_mtokdollar` | float | IQ per million tokens / per $M tokens |
| `iq_per_1k_pt` / `cost_per_iq_pt` | float | IQ per 1k points / cost per IQ point (Cost per IQ tab) |
| `tokens_m` | float | Output tokens in millions (AA eval; verbosity, not quality) |
| `speed_tps` | float | Output tokens per second |
| `ttft` | float | Time to first token (s) |
| `inp_price` / `out_price` | float | $/M input / output tokens (AA) |
| `cache_hit_price` | float | $/M cached input tokens (AA) |
| `openrouter_inp_price_per_m` / `openrouter_out_price_per_m` / `openrouter_cache_read_price_per_m` | float | OpenRouter pricing |
| `openrouter_vendor` | string | OpenRouter vendor tag |
| `context_window` | int | Context window in tokens (OpenRouter `context_length`); drives crossover bubble size |
| `arena_code_elo` / `arena_code_ci` / `arena_code_votes` | float | Chatbot Arena Code |
| `arena_text_elo` / `arena_text_ci` / `arena_text_votes` | float | Chatbot Arena Text |
| `aa_coding_index` / `aa_gpqa` / `aa_hle` / `aa_ifbench` / `aa_lcr` / `aa_scicode` / `aa_tau2` / `aa_tau_banking` / `aa_terminalbench_hard` / `aa_terminalbench_v2_1` / `aa_omniscience_hallucination_rate` / `aa_briefcase_analytical_quality_elo` / `aa_briefcase_presentation_elo` / `aa_time_per_task` | float | AA live-API eval scores (0–1) |
| `omniscience_index` / `omniscience_accuracy` / `omniscience_hallucination_rate` | float | Omniscience composite |
| `briefcase_elo` / `briefcase_analytical_quality_elo` / `briefcase_presentation_elo` / `briefcase_rubric_score` | float | Briefcase Elo |
| `agentic_index` / `coding_index` | float | Composite indices |
| `radar_intel` / `radar_speed` / `radar_cache_eff` / `radar_cost_eff` / `radar_ctx` | float | Normalized radar values (Provider Archetypes) |
| `archetype` | string | "frontier" / "sweet-spot" / "premium" / "budget" / "commodity" / "mid-tier" |
| `pareto_optimal` | bool | On the IQ-vs-cost frontier |
| `cost_percentile` / `iq_percentile` | float | Ranking percentiles |
| `has_breakdown` | bool | True if AA cost-segment data exists (Cost Breakdown tab) |
| `useful_cost` / `reasoning_tax_pct` | float | Derived cost metrics |
| `blended` | bool | Blended/eval-average model |
| `release_date` | string | Model release date (AA live API) |

Cost Breakdown segments (Input / Cached / Answer / Reasoning) are computed at render time by `cost-breakdown.js` from `cost_seg_*` when present on the source model — they are not stored on the projection row.

## Shared config (`_shared.js`)

- `window.CREATOR_COLORS` — creator → hex color map (24 creators)
- `window.VIZ_REGISTRY` — array of `{id, name, subtitle, render}`
- `window.__legendFilter` — global filter state `{ dim, val } | null`
- `window.__setLegendFilter(dim, val)` — toggle helper
- `window.__modelOpacity(m)` — returns 0–1 for fade effect based on filter
- `window.__filterSubscribers` — `Set` of callbacks invoked on filter change
- `window.__renderCreatorLegend()` — generates HTML legend strip
- `window.SKU_PATTERNS` — slug → suffix splits (OSS / Mini / Nano / Flash / Code)
- `window.RADAR_AXES` — 5 radar axes (key, label, angle)
- `window.COST_SEGMENTS` — color + label for cost breakdown
- `window.FIELD_LABELS` — display names for table columns
- `window.CACHE_HIT_RATES` — observed rates from Dirac.run / OpenRouter

## Shell globals (defined in dashboard.html)

- `buildTooltip(model)` — full data tooltip builder
- `attachTooltip(el, model)` — convenience: attaches mouseenter/move/leave
- `getTooltipEl()` — returns the shared `#tooltip` div
- `window.PROCESSED_DATA` — the raw generated dataset object
- `window.MODELS` — array of all models (117), after the `_domain.js` load boundary

## Current viz files

- `_result.js` — `Result` (`ok`/`err`/`fromFn`) + `Pipeline` (JS port of `data/_pipeline.Pipeline`)
- `_domain.js` — `ProjectionRow.load` boundary; populates `window.MODELS`
- `_shared.js` — shared state, config, tooltip wiring
- `_boot.js` — boot orchestration pipeline
- `crossover.js` — scatter with x/y axis dropdowns, bubble size = context window
- `cost-breakdown.js` — stacked bars with cache hit rate toggle
- `provider-archetypes.js` — radar charts per creator
- `cost-per-iq.js` — cost per IQ point bar chart
- `data-table.js` — sortable, filterable multi-view table (multi-column sort with shift+click)

## Testing locally

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Black-box JS tests (`tests/test_*_js.js`) load `data/processed.js` under Node with a DOM stub and assert pure-transform behavior — no jsdom, stub at the boundary.
