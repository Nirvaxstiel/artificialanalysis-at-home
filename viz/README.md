# Viz Worker Contract

Each viz is a self-contained JS file in this directory. The dashboard shell loads all of them and uses the registry to switch views.

## File template

```js
// viz/NN-slug.js
(function() {
  function render(container, data) {
    // data = processed.js.models (array)
    // container = DOM element to mount into
    // ... build your SVG/HTML ...
  }

  // Register with the shell
  window.VIZ_REGISTRY = window.VIZ_REGISTRY || [];
  window.VIZ_REGISTRY.push({
    id: 'NN',
    name: 'Human Title',
    subtitle: 'One-line description',
    render
  });
})();
```

## Rules

1. **Read-only inputs.** `data/processed.js` is the only data source. Don't write to it.
2. **Self-contained styles.** Inline `<style>` in your container, or use the CSS custom properties from `dashboard.html` (`--neon`, `--neon2`, `--bg`, `--fg`, `--muted`, `--border`).
3. **Reuse the tooltip.** If you have hoverable elements, attach to the shared `#tooltip` div from `dashboard.html` using the `buildTooltip(model)` function (also exposed globally).
4. **No external dependencies.** No CDN, no fetch, no imports. Pure DOM + SVG.
5. **Match the brutalist aesthetic.** Hard borders, monospace, neon accents, `//` comments.
6. **No hardcoded values.** Use `window.FIELD_LABELS`, `window.RADAR_AXES`, `window.SKU_PATTERNS`, `window.COST_SEGMENTS` from `_shared.js`.
7. **Use the legend filter.** Read `window.__legendFilter` to dim non-matching elements.

## Available data (from `processed.js`)

| Field | Type | Notes |
|-------|------|-------|
| `slug` | string | URL identifier (hyphenated) |
| `name` | string | Display name (may include effort qualifiers) |
| `creator` | string | Model creator org |
| `type` | string | "Proprietary" or "Open weights" |
| `intel` | int | AA Intelligence Index v4.1 |
| `inp_price` | float | $/M input tokens (uncached) |
| `out_price` | float | $/M output tokens |
| `cache_hit_price` | float | $/M cached input tokens |
| `speed_tps` | float | Output tokens per second |
| `tokens_m` | float | Output tokens in millions (from AA eval) |
| `cost_per_task` | float | USD per task (old data only, ~29/85) |
| `cost_seg_total` | float | Per-task total (AA breakdown) |
| `cost_seg_input` | float | Per-task input cost |
| `cost_seg_cache_hit` | float | Per-task cache hit cost |
| `cost_seg_cache_write` | float | Per-task cache write cost |
| `cost_seg_answer` | float | Per-task answer cost |
| `cost_seg_reasoning` | float | Per-task reasoning cost |
| `livebench_average` | float | LiveBench score (17/85) |
| `arena_code_elo` | float | Chatbot Arena Code Elo (18/85) |
| `openrouter_inp_price_per_m` | float | OR pricing (49/85) |
| `params_b` | float | Parameters in billions (24/85, AA page) |
| `archetype` | string | "frontier"/"sweet-spot"/"premium"/"budget"/"commodity"/"mid-tier" |
| `pareto_optimal` | bool | On the IQ-vs-cost frontier |

## Shared config (`_shared.js`)

- `window.CREATOR_COLORS` — creator → hex color map (24 creators)
- `window.VIZ_REGISTRY` — array of `{id, name, subtitle, render}`
- `window.__legendFilter` — global filter state `{ dim, val } | null`
- `window.__setLegendFilter(dim, val)` — toggle helper
- `window.__modelOpacity(m)` — returns 0-1 for fade effect based on filter
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
- `window.PROCESSED_DATA` — array of all models (85)

## Current viz files

- `_shared.js` — shared state, config, tooltip wiring
- `01-crossover.js` — scatter with x/y axis dropdowns, bubble size
- `02-reasoning-tax.js` — stacked bars with cache hit rate toggle
- `03-provider-archetypes.js` — radar charts per creator
- `04-speed-cost.js` — speed × cost scatter with sweet-spot
- `05-cost-per-iq.js` — cost per IQ point bar chart
- `06-data-table.js` — sortable, filterable table

## Testing locally

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```
