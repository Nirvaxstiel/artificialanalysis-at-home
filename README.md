# aa-at-home

**LLM benchmark analytics — derived from the public charts at [artificialanalysis.ai](https://artificialanalysis.ai/).**

Built because the AA Pro API is paywalled. The free tier shows charts but not the underlying data, so we read the charts (vision OCR) and the model summary cards (HTML scrape) to reconstruct the data we need for crossover analysis.

## What it is

A static HTML dashboard that overlays three axes AA charts separately:

- **Intelligence Index** (cost-effectiveness) — the y-axis
- **Cost per Task** (USD, log scale) — the x-axis
- **Output Tokens per Task** (bubble size)

Plus a hover tooltip with per-model cost breakdown (reasoning vs answer vs cache write vs cache hit vs input), and a sortable leaderboard ranked by IQ per $1000.

## Why

AA's own charts are great for individual axes. They don't let you ask "is the cheap model also the verbose one, and is that verbosity the reason it's cheap?" — that's a 3-axis question, and the answer changes your model pick.

## Stack

- **No build step.** No framework, no CDN, no bundler.
- **One HTML file** (`dashboard.html`) — embeddable anywhere that can serve static files.
- **Two JSON files** in `data/` — the scraped dataset and the cost breakdown.
- **Vanilla JS** for the chart and tooltip. ~50 lines total.

Run it:
```bash
cd "LLM Provider Pricing Analysis"
python -m http.server 8000
# open http://localhost:8000/dashboard.html
```

Or just open `dashboard.html` directly in any modern browser.

## Data provenance

- **Scraped**: per-model summary cards at `artificialanalysis.ai/models/{slug}` (Intelligence Index, $/M input/output/cache, total cost, total tokens, speed).
- **Vision-extracted**: bar chart values from AA's public charts (Cost per Task breakdown, Output Tokens per Task, Intelligence × Cost scatter).

Data is current as of **3 July 2026**, AA Intelligence Index v4.1 (9 weighted evals: GDPval-AA v2, τ³-Banking, Terminal-Bench v2.1, SciCode, HLE, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR).

## Caveats

- Cost segment splits (reasoning/answer/cache write/cache hit/input) are estimated from color ratios in the bar chart, not read from raw numbers. Total bar values are exact (read from labels).
- Free-tier models (Solar Pro 3, K2 Think V2, Muse Spark) have $0 list price and are excluded from the scatter.
- ~28 of 38 models have full cost+tokens data. The rest show up in the leaderboard as best-effort.

## Layout

```
.
├── README.md
├── dashboard.html              ← the viz
├── LLM Provider Pricing Analysis.md  ← Obsidian note (also the source of the source-images folder above)
└── data/
    ├── aa_model_data.json      ← primary dataset (38 models, 17 fields)
    ├── aa_model_data.csv       ← same, CSV
    └── aa_cost_breakdown.json  ← per-task cost segments (28 models)
```

## License

Data: scraped from public web pages. Verify against AA before quoting.
Code: do whatever you want.
