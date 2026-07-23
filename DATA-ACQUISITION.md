# Data Acquisition Reference

How every source in the pipeline is **obtained** — method, auth, script, freshness, and repro steps. This complements `LLM Provider Pricing Analysis.md` (what each source is *used for*) and `README.md` (build order and orchestrator modes).

> **Golden rule:** `_build_registry.py` reads raw source files only — never pipeline output. Each source below lands as a file under `data/sources/`; the build scripts consume files, not live endpoints. The only network access in the pipeline is `_pull_sources.py` (OpenRouter / LiveBench / OpenLLM), invoked by the full build only.

## Acquisition matrix

| # | Source | Method | Auth | Acquired by | File(s) | Freshness |
|---|--------|--------|------|-------------|---------|-----------|
| 1 | Artificial Analysis (scraped) | **Web page scraping** | none (public) | External AA scraper → dropped into repo | `aa/raw/aa_models_scraped.json`, `aa/enriched/aa_model_data.json`, `aa/enriched/aa_cost_breakdown.json` |
| 1A | AA intelligence/benchmark charts | **SVG scrape (method-2)** — PRIMARY | none (public) | Browser console query → `aa_charts_export.json` (inside repo) → `aa` source | `aa_charts_export.json` |
| 1B | AA intelligence/benchmark charts | **JSON-LD console export** | none (public) | AA page console query → `aa_jsonld_export.json` (inside repo) → merged into `aa` source as Step 0b (fills gaps method-2 doesn't cover) | `aa_jsonld_export.json` |
| 2 | Artificial Analysis (live API) | **REST API pull** | `x-api-key` (AA_API_KEY in Hermes `.env`) | Manual `curl`/script → `aa_api_live.json` | `aa/aa_api_live.json` (579 models) | pulled 2026-07-23 |
| 3 | OpenRouter | **REST API pull** | none (public) | `_pull_sources.py` | `openrouter_models.json` (~342 models) | on full build (pull) |
| 5 | LiveBench | **CSV download** (GitHub raw) | none | `_pull_sources.py` | `livebench_2026_01_08.csv`, `livebench_categories_2026_01_08.json` | pinned date 2026-01-08 |
| 6 | OpenLLM v2 | **Parquet file** (manually placed) | none | Downloaded separately → `openllm_v2.parquet`, then `_pull_sources.py` reads it | `openllm_v2.parquet` → `openllm_aa_subset.json` | manual, not fetched by script |
| 7 | Dirac.run | **HTML table parse** | none | Fetch `dirac.run/posts/cache-hit-rates-agents`, parse the `#the-full-table` `<table>` → `cache_hit_rates.json` | `dirac/cache_hit_rates.json` (398 rows) | 2026-07-23 |
| 8 | Chatbot Arena (Code + Text) | **JSON download** (manual) | none | Downloaded leaderboard JSON → dropped into repo | `arena_code.json`, `arena_text.json` | manual, per snapshot |

## Per-source detail

### 1. Artificial Analysis — scraped (primary)
- **Method:** HTML scraping of AA model pages (intelligence index, $/M, speed, output tokens, params, cost segments).
- **Script:** lives **outside this repo** (the "AA scraper"). It writes `aa/raw/aa_models_scraped.json` (99 raw) and `aa/enriched/aa_model_data.json` (blended) into the repo.
- **Repro:** run the external scraper, then the standard build. Not automatable from here.
- **Caveat:** the old vision/OCR image-chart source and its ingestion code were removed — its metrics (Omniscience, Briefcase Elo, agentic/coding indices) are covered by the SVG scrape (#1A) / JSON-LD (#1B), which need no vision.

### 1A. Artificial Analysis — SVG scrape (`aa_charts_export.json`)  ← PRIMARY
  - **Method:** the AA site renders every chart as an inline **SVG** (recharts). A console snippet grabs each chart section (`[dir=ltr].scroll-mt-24`) → its `<svg>` outerHTML + visible `<span>` texts (title/subtitle/desc). The export is `data/sources/aa/aa_charts_export.json`: a JSON array of `{ svg, spans }`, one entry per chart (16 entries total; scatter charts carry no `<a>`/value text and are skipped by the parser).
  - **Why this over #1B (JSON-LD):** the SVG charts embed **model slugs** in `<a href="/models/{slug}">` and the metric value in `<text>` nodes. A Python parser (`data/sources/aa/_parse_charts.py`) pairs them by render order → clean `slug → value`. No vision, no OCR, no manual transcription. This is the **authoritative AA chart source**; #1B JSON-LD fills only the gaps method-2 doesn't cover.
  - **Coverage (this export):** Intelligence Index (107, "by Open Weights" bar chart), Briefcase Elo (36, 2 values/model: analytical + presentation), Omniscience Hallucination Rate (105, rendered as `89%` → stored `0.89`), Time per Intelligence Index Task (62), Pricing (95). **AA removed the standalone Coding Index and Cost to Run bar charts** — those metrics now come from the JSON-LD export (#1B) instead (`aa_coding_index`, `cost_segments.*`). The parser matches charts by title (`spans[0]`), not position, so a re-order/removal on AA's side can't silently mis-map data; empty (scatter) charts are skipped.
  - **Value normalization:** parser strips `$` (pricing), `%` (omniscience → fraction), `&lt;`/`<` (less-than sentinel), thousands commas. Rounds to the SVG label precision (e.g. `0.3` not `0.2963` — the precise value lives in JSON-LD if needed).
  - **Pricing chart — SOLVED:** the 3 `recharts-label-list` groups correspond to the 3 series named in the chart title ("Cache Hit, Input, and Output"). Each value `<text>` carries an `x` coordinate; aligning values to model columns by `x` (rounding to the per-model band) yields per-model `cache_hit_price` / `inp_price` / `out_price`. Validated against the live API for `gpt-oss-20b` (0.05/0.2) and `claude-opus-4-8` (5/25) — exact match. All 12 gpt-5.6 models gain pricing this way. Parsed by `_parse_pricing()`.
  - **Repro (scrape script `scraped-method-2.js`):**
    ```js
    // In the AA page console — capture each chart section as { svg, spans }.
    JSON.stringify(Array.from(document.querySelectorAll('[dir=ltr].scroll-mt-24'))
      .map(el => ({ svg: el.querySelector('svg[role]')?.outerHTML || '',
                    spans: Array.from(el.querySelectorAll('span')).map(s => s.textContent) })))
    ```
    Save the array as `data/sources/aa/aa_charts_export.json`.

### 1B. Artificial Analysis — JSON-LD console query (`aa_jsonld_export.json`)
  - **Method:** the AA site renders its charts from **schema.org `Dataset` JSON-LD** embedded in the page. A browser-console query returns the structured data directly — **no HTML scraping, no image vision, no manual table-copy.** This is the "real way to query" the site.
  - **File:** `data/sources/aa/aa_jsonld_export.json` (committed; copy a fresh export here on each refresh).
  - **Shape:** a JSON array of `Dataset` objects (one per chart). Each `data[]` entry has `label`, `detailsUrl` (→ slug, e.g. `/models/gpt-5-6-sol-medium`), and metric fields:
    - `Intelligence` / `Artificial Analysis Intelligence Index by Open Weights / Proprietary` → `intel` (the two are **value-identical** on shared slugs; the Open-Weights one is the superset, so only it feeds `intel`)
    - `Speed` (`medianOutputSpeed`) → `speed_tps`
    - `Cost per Task` (`costPerIntelligenceIndexTask`) → `cost_per_task`
    - `Artificial Analysis Coding Index` (`codingIndex`) → `aa_coding_index`
    - `AA-Omniscience Hallucination Rate` (`omniscienceHallucinationRate`) → `omniscience_hallucination_rate`
    - `AA-Briefcase Analytical Quality & Presentation Elo` (`aaBriefcaseQualityElos[]`) → `briefcase_analytical_quality_elo` / `briefcase_presentation_elo`
    - `Time per Intelligence Index Task` (`timePerTask`) → `time_per_task`
    - `Cost to Run Artificial Analysis Intelligence Index` (5 fields) → `cost_segments.*`
    - `Pricing: Cache Hit, Input, and Output` (`pricing[]`) → `inp_price` / `out_price`
  - **Role in pipeline:** `get_aa_jsonld_models()` runs as **Step 0b** of `get_aa_models()` (after method-2, Step 0), *seeding NEW models* and filling authoritative `aa.*` metrics that method-2 didn't capture. Later sources enrich fill-nulls-only via `_merge_fill_nulls`.
  - **Repro:**
    ```js
    // In the AA page console (e.g. ?models=gpt-5-6-...):
    JSON.stringify(Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
      .map(s => JSON.parse(s.textContent)))
    ```
    Save the array as `data/sources/aa/aa_jsonld_export.json`.
  - **Known gap:** the JSON-LD export only contains models **currently in the rendered view**. To get full coverage (e.g. Pricing for all 12 GPT-5.6 variants), query each chart/category **separately in batches** and merge the exports. The Pricing dataset is frequently absent from a single view — re-run the query with the Pricing chart in view.
  - **Role:** ingested as Step 0b — fills ONLY the fields method-2 (#1A) didn't capture (method-2 is the superset and wins on overlap).

### 2. Artificial Analysis — live API (`aa_api_live.json`)
- **Method:** `GET https://artificialanalysis.ai/api/v2/data/llms/models` with header `x-api-key: ***`
- **Auth:** free-tier key (100 req/day). Key stored in Hermes `.env` as `AA_API_KEY` — **never hardcode**.
- **Payload:** `status`, `prompt_options`, `data[]` (572 models). Each has `slug`, `release_date`, `model_creator.name`, `evaluations{}` (16 scores: hle, gpqa, aime, aime_25, scicode, lcr, terminalbench_v2_1, …).
- **Repro:**
  ```bash
  curl -s -H "x-api-key: $AA_API_KEY" https://artificialanalysis.ai/api/v2/data/llms/models \
    | python -m json.tool > data/sources/aa/aa_api_live.json
  ```
- **Used for:** `release_date`, `creator` backfill, 16 live-AA benchmark axes.

### 3. OpenRouter (`openrouter_models.json`)
- **Method:** `GET https://openrouter.ai/api/v1/models` (public, no auth).
- **Script:** `_pull_sources.py` → `openrouter_models.json`.
- **Key fields:** `pricing.prompt`, `pricing.completion`, `pricing.input_cache_read/write`, `context_length` (→ `context_window`).
- **Repro:** `python data/_pull_sources.py`.

### 5. LiveBench
- **Method:** CSV + JSON from GitHub raw (pinned snapshot `2026_01_08`).
- **Script:** `_pull_sources.py` downloads both files.
- **Repro:** `python data/_pull_sources.py`.

### 6. OpenLLM v2
- **Method:** **parquet file**, manually downloaded and placed at `data/sources/openllm_v2.parquet`. `_pull_sources.py` reads it (does NOT fetch it).
- **Script:** `_pull_sources.py` reads local parquet → `openllm_aa_subset.json` (keyword-filtered to AA-relevant models).
- **Repro:** download parquet externally first, then `python data/_pull_sources.py`.

### 7. Dirac.run (`dirac/cache_hit_rates.json`)
- **Method:** fetch `dirac.run/posts/cache-hit-rates-agents`, parse the `#the-full-table` `<table>` (the page renders the full table in HTML; extract `<tr>` rows → `model`, `provider`, `eff_input_price`, `eff_output_price`, `cache_hit_rate`). A one-off Python parse (`urllib` + regex on `<table>`) writes `cache_hit_rates.json` — no manual transcription needed.
- **No API.** 398 rows: `model`, `provider`, `cache_hit_rate`, `eff_input_price`, `eff_output_price`.
- **Semantics:** observed % of input served from prefix cache — distinct from AA's `cache_hit_price` ($/Mtok read price). Never conflate.
- **Repro:** re-fetch + re-parse when a new snapshot posts.

### 8. Chatbot Arena (Code + Text)
- **Method:** **manual JSON download** of the leaderboard → `arena_code.json` / `arena_text.json` (each has `meta` + `models[]`).
- **Not fetched by any script.** Place files manually; `_build_registry.py` consumes them.

## What `_pull_sources.py` actually covers
Only **#4 OpenRouter, #5 LiveBench, #6 OpenLLM v2** are fetched by the script. The other sources (#1, #1A, #1B, #2, #8) are acquired **manually** (scrape / console-query / API curl / JSON download) and committed as files. #7 (Dirac.run) is fetched by a one-off `urllib`+regex table parse (no clean API endpoint, but no manual transcription). This is by design — those sources require keys/console-query or have no stable endpoint.

> **AA is ONE unified source, not separate streams.** Scraped (#1), SVG scrape (#1A), JSON-LD console-query (#1B), and live-API (#2) all feed the same `aa.*` namespace via `get_aa_models()` merge. The SVG scrape (#1A) is now the preferred way to add new models + authoritative metrics without vision/scraping.

## Repro checklist (full refresh)

```bash
# Manual (outside script):
#  - run external AA scraper → aa/raw + aa/enriched
#  - copy aa_charts_export.json (SVG console scrape of AA page) → aa/      (PRIMARY)
#  - copy aa_jsonld_export.json (JSON-LD console query of AA page) → aa/  (fills gaps)
#  - curl AA live API → aa/aa_api_live.json   (needs AA_API_KEY)
#  - parse Dirac table → dirac/cache_hit_rates.json
#  - download Arena JSON → arena_code.json, arena_text.json
#  - download openllm_v2.parquet → data/sources/

# Full build (network pull of OpenRouter/LiveBench/OpenLLM, then registry → axes → dashboard):
python -m data._pipeline            # no arg → build() pulls + builds

# Offline rebuild (uses committed sources, no network):
python -m data._pipeline build      # or: build_from_cache
```

`_pull_sources.py` itself (with no arg) only fetches OpenRouter / LiveBench / OpenLLM v2. The manual sources above are committed files consumed by `_build_registry` regardless of pull.
