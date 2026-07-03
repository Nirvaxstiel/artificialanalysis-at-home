# Viz Worker Contract

Each viz is a self-contained JS file in this directory. The dashboard shell loads all of them and uses the registry to switch views.

## File template

```js
// viz/NN-slug.js
(function() {
  const CREATOR_COLORS = window.CREATOR_COLORS || {};  // shared, defined in dashboard.html
  const TT_STYLES = `
    /* tooltip styles go here if you need them; otherwise inherit from dashboard */
  `;

  function render(container, data) {
    // data = processed.json.models (array)
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

1. **No file overlap.** Each worker owns exactly one file. Branch + worktree per file.
2. **Read-only inputs.** `data/processed.json` is the only data source. Don't write to it.
3. **Self-contained styles.** Inline `<style>` in your container, or use the CSS custom properties from `dashboard.html` (`--neon`, `--neon2`, `--bg`, `--fg`, `--muted`, `--border`).
4. **Reuse the tooltip.** If you have hoverable elements, attach to the shared `#tooltip` div from `dashboard.html` using the `buildTooltip(model)` function (also exposed globally). Fallback: roll your own.
5. **No external dependencies.** No CDN, no fetch, no imports. Pure DOM + SVG.
6. **Match the brutalist aesthetic.** Hard borders, monospace, neon accents, `//` comments. Reference: `dashboard.html` CSS.

## Available data (from `processed.json`)

| Field | Type | Notes |
|---|---|---|
| `slug` | string | URL identifier |
| `name` | string | Display name |
| `creator` | string | Model creator org |
| `type` | string | "Proprietary" or "Open weights" |
| `intel` | int | AA Intelligence Index v4.1 |
| `cost_per_task` | float | USD per task (from breakdown JSON) |
| `tokens_m` | float | Output tokens in millions |
| `speed_tps` | float | Output tokens per second |
| `inp_price` | float | $/M input tokens |
| `out_price` | float | $/M output tokens |
| `iq_per_dollar_pt` | float | IQ / cost_per_task (raw cost efficiency) |
| `iq_per_mtok` | float | IQ / tokens_m (verbosity-adjusted smartness) |
| `iq_per_mtokdollar` | float | IQ / (cost × tokens) — **THE money metric** |
| `useful_cost` | float | cost minus reasoning tax |
| `reasoning_tax_pct` | float | % of useful cost spent on thinking |
| `cost_per_wallsec` | float | $ per wall-clock-second (time-as-money) |
| `archetype` | string | "sweet-spot" / "brute-frontier" / "commodity" / "dead-weight" / "mid" / "unknown" |
| `pareto_optimal` | bool | On the IQ-vs-cost frontier |
| `cost_percentile` | float | 0-100, 100 = cheapest |
| `iq_percentile` | float | 0-100, 100 = smartest |
| `has_breakdown` | bool | Has per-task cost segment data |

## Shell globals (defined in dashboard.html)

- `window.CREATOR_COLORS` — creator → hex color map
- `window.VIZ_REGISTRY` — array of `{id, name, subtitle, render}`
- `buildTooltip(model)` — full data tooltip builder
- `attachTooltip(el, model)` — convenience: attaches mouseenter/move/leave to use buildTooltip
- `getTooltipEl()` — returns the shared `#tooltip` div

## Branches

- `main` — dashboard.html + data/ + this contract
- `viz/01-reasoning-tax` — worker 1
- `viz/02-pareto-reasoning` — worker 2 (reference impl, may already be merged)
- `viz/03-provider-archetypes` — worker 3
- `viz/04-speed-cost` — worker 4
- `viz/05-verbosity-archetype` — worker 5
- `viz/06-cost-per-iq` — worker 6

After your viz is done:
```bash
git checkout main
git merge --no-ff viz/NN-name
# if conflict, fix only dashboard.html (which lists the <script src> includes)
```

## Testing locally

```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
# use the nav bar to switch to your viz
```
