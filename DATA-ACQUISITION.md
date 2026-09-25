# Data Acquisition Reference

How every source in the pipeline is **obtained** — method, auth, script, freshness, and repro steps. This complements `LLM Provider Pricing Analysis.md` (what each source is *used for*) and `README.md` (build order and orchestrator modes).

> **Golden rule:** `_build_registry.py` reads raw source files only. It never reads pipeline output. Each source below lands as a file under `data/sources/`. The build scripts consume files, not live endpoints. `_pull_sources.py` fetches the AA public catalog, OpenRouter, LiveBench, and Dirac.run. It also processes the local OpenLLM parquet file. The keyed AA REST snapshot is pulled separately.
>
> Snapshot dates and per-source model counts are declared once in `data/_build_registry.py` (`SOURCE_NAMES`, `UNDATED_SNAPSHOTS`, `SOURCE_NOTES`). The build reads the Arena and LiveBench dates from the source files. It generates all of these values into `model_registry.json` meta (`source_meta`) → `processed.js` meta (`sources_meta`). The dashboard footer shows them. The Freshness column below mirrors that generated meta.

## Acquisition matrix

| # | Source | Method | Auth | Acquired by | File(s) | Freshness |
|---|--------|--------|------|-------------|---------|-----------|
| 1 | Artificial Analysis (scraped) | **Web page scraping** | none (public) | External AA scraper → dropped into repo | `aa/raw/aa_models_scraped.json`, `aa/enriched/aa_model_data.json`, `aa/enriched/aa_cost_breakdown.json` | AA snapshot 2026-09-10 |
| 1A | AA intelligence/benchmark charts | **SVG scrape (method-2)** — PRIMARY | none (public) | Browser console query → `aa_charts_export.json` (inside repo) → `aa` source | `aa_charts_export.json` | AA snapshot 2026-09-10 |
| 1B | AA intelligence/benchmark charts | **JSON-LD console export** | none (public) | AA page console query → `aa_jsonld_export.json` (inside repo) → merged into `aa` source as Step 0b (fills gaps method-2 doesn't cover) | `aa_jsonld_export.json` | AA snapshot 2026-09-10 |
| 2 | Artificial Analysis (live API) | **REST API pull** | `x-api-key` (`AA_API_KEY` in Hermes `.env`) | Manual authenticated pull → `aa_api_live.json` | `aa/aa_api_live.json` (671 models) | pulled 2026-09-24 |
| 2A | Artificial Analysis (public model catalog) | **Next.js RSC page payload** | none | `_pull_sources.py` | `aa/aa_public_model_catalog.json` (671 variants) | on full build (pull) |
| 3 | OpenRouter | **REST API pull** | none (public) | `_pull_sources.py` | `openrouter_models.json` (~342 models) | on full build (pull) |
| 5 | LiveBench | **CSV download** (GitHub raw) | none | `_pull_sources.py` | `livebench_2026_01_08.csv`, `livebench_categories_2026_01_08.json` | pinned date 2026-01-08 |
| 6 | OpenLLM v2 | **Parquet file** (manually placed) | none | Downloaded separately → `openllm_v2.parquet`, then `_pull_sources.py` reads it | `openllm_v2.parquet` → `openllm_aa_subset.json` | manual, not fetched by script |
| 7 | Dirac.run | **HTML table parse** (automated) | none | `_pull_sources.py` → `sources/dirac/_fetch.py`: fetch `dirac.run/posts/cache-hit-rates-agents`, parse `#the-full-table` → `cache_hit_rates.json` + `provider_rates.json` | `dirac/cache_hit_rates.json` (398 rows), `dirac/provider_rates.json` (68 providers) | on full build (pull) |
| 8 | Chatbot Arena (Code + Text) | **JSON download** (manual) | none | Downloaded leaderboard JSON → dropped into repo | `arena_code.json`, `arena_text.json` | fetched 2026-07-04 |
| 9 | misc.json (context-window overlay) | **Hand-written JSON** | none | Maintained in-repo; fills `meta.context_window` where OpenRouter has no entry | `misc.json` (43 models) | 2026-07-10 |

## Per-source detail

### 1. Artificial Analysis — scraped (primary)
- **Method:** HTML scraping of AA model pages (intelligence index, $/M, speed, output tokens, params, cost segments).
- **Script:** lives **outside this repo** (the "AA scraper"). It writes `aa/raw/aa_models_scraped.json` (99 raw) and `aa/enriched/aa_model_data.json` (blended) into the repo.
- **Repro:** run the external scraper, then the standard build. Not automatable from here.
- **Caveat:** the old vision/OCR image-chart source and its ingestion code were removed. The SVG scrape (#1A) and JSON-LD (#1B) cover its metrics (Omniscience, Briefcase Elo, agentic/coding indices). Neither method needs vision.

### 1A. Artificial Analysis — SVG scrape (`aa_charts_export.json`)  ← PRIMARY
  - **Method:** the AA site renders every chart as an inline **SVG** (recharts). A console snippet grabs each chart section (`[dir=ltr].scroll-mt-24`) → its `<svg>` outerHTML + visible `<span>` texts (title/subtitle/desc). The export is `data/sources/aa/aa_charts_export.json`: a JSON array of `{ svg, spans }`, one entry per chart. The export holds 16 entries. Scatter charts carry no `<a>` or value text, and the parser skips them.
  - **Why this over #1B (JSON-LD):** the SVG charts embed **model slugs** in `<a href="/models/{slug}">` and the metric value in `<text>` nodes. A Python parser (`data/sources/aa/_parse_charts.py`) pairs them by render order → clean `slug → value`. No vision, no OCR, no manual transcription. This is the **authoritative AA chart source**. #1B JSON-LD fills only the gaps that method-2 does not cover.
  - **Coverage (this export):** Intelligence Index (108, "by Open Weights" bar chart), Briefcase Elo (36, 2 values/model: analytical + presentation), Omniscience Hallucination Rate (106, rendered as `89%` → stored `0.89`), Time per Intelligence Index Task (65), Pricing (97). **AA removed the standalone Coding Index and Cost to Run bar charts.** As of 31 Jul 2026, AA also dropped the `Artificial Analysis Coding Index` dataset from the JSON-LD export. `coding_index` is therefore no longer an AA source, and it is absent from the registry. The parser matches charts by title (`spans[0]`), not by position. A re-order or a removal on the AA side cannot silently mis-map data. The parser skips empty (scatter) charts. AA's chart sections are **lazy-loaded**. Scroll each `.scroll-mt-24` block into view before you run the scrape. If you do not, you capture only lucide page-icon SVGs. The scrape captures `svg[role].recharts-surface` (44 chart-blocks = 22 charts × 2).
  - **Value normalization:** the parser strips `$` (pricing), `%` (omniscience → fraction), `&lt;`/`<` (less-than sentinel), and thousands commas. It rounds to the SVG label precision. For example, it stores `0.3`, not `0.2963`. The precise value lives in JSON-LD if you need it.
  - **Pricing chart — SOLVED:** the 3 `recharts-label-list` groups correspond to the 3 series named in the chart title ("Cache Hit, Input, and Output"). Each value `<text>` carries an `x` coordinate. Align the values to the model columns by `x` (round each value to the per-model band) to get per-model `cache_hit_price` / `inp_price` / `out_price`. The result matches the live API for `gpt-oss-20b` (0.05/0.2) and `claude-opus-4-8` (5/25) exactly. All 12 gpt-5.6 models gain pricing this way. Parsed by `_parse_pricing()`.
  - **Repro (scrape script `scraped-method-2.js`):**
    ```js
    // In the AA page console — capture each chart section as { svg, spans }.
    JSON.stringify(Array.from(document.querySelectorAll('div[id].scroll-mt-24'))
      .map(el => ({ svg: el.querySelector('svg[role=application]')?.outerHTML || '',
                    spans: Array.from(el.querySelectorAll('span')).map(s => s.textContent) })))
    ```
    Save the array as `data/sources/aa/aa_charts_export.json`.

### 1B. Artificial Analysis — JSON-LD console query (`aa_jsonld_export.json`)
  - **Method:** the AA site renders its charts from **schema.org `Dataset` JSON-LD** embedded in the page. A browser-console query returns the structured data directly. It needs **no HTML scraping, no image vision, and no manual table-copy.** This is the "real way to query" the site.
  - **File:** `data/sources/aa/aa_jsonld_export.json` (committed, copy a fresh export here on each refresh).
  - **Shape:** a JSON array of `Dataset` objects (one per chart). Each `data[]` entry has `label`, `detailsUrl` (→ slug, for example `/models/gpt-5-6-sol-medium`), and metric fields:
    - `Intelligence` / `Artificial Analysis Intelligence Index by Open Weights / Proprietary` → `intel` (on shared slugs the two agree exactly, and only the Open-Weights superset feeds `intel`)
    - `Speed` (`medianOutputSpeed`) → `speed_tps`
    - `Cost per Task` (`costPerIntelligenceIndexTask`) → `cost_per_task`
    - `Artificial Analysis Coding Index` (`codingIndex`) → `aa_coding_index` — **REMOVED by AA (31 Jul 2026)**: the dataset is no longer in the JSON-LD export or in the charts. `aa_coding_index` is now unsourced and absent from the registry.
    - `AA-Omniscience Hallucination Rate` (`omniscienceHallucinationRate`) → `omniscience_hallucination_rate`
    - `AA-Briefcase Analytical Quality & Presentation Elo` (`aaBriefcaseQualityElos[]`) → `briefcase_analytical_quality_elo` / `briefcase_presentation_elo`
    - `Time per Intelligence Index Task` (`timePerTask`) → `time_per_task`
    - `Cost to Run Artificial Analysis Intelligence Index` (5 fields) → `cost_segments.*`
    - `Pricing: Cache Hit, Input, and Output` (`pricing[]`) → `inp_price` / `out_price`
  - **Role in pipeline:** `get_aa_jsonld_models()` runs as **Step 0b** of `get_aa_models()` (after method-2, Step 0). It *seeds NEW models* and fills authoritative `aa.*` metrics that method-2 does not capture. Later sources enrich fill-nulls-only via `_merge_fill_nulls`.
  - **Repro:**
    ```js
    // In the AA page console (e.g. ?models=gpt-5-6-...):
    JSON.stringify(Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
      .map(s => JSON.parse(s.textContent)))
    ```
    Save the array as `data/sources/aa/aa_jsonld_export.json`.
  - **Known gap:** the JSON-LD export only contains models **currently in the rendered view**. For full coverage (for example, Pricing for all 12 GPT-5.6 variants), query each chart or category **separately in batches**, then merge the exports. The Pricing dataset is frequently absent from a single view. Re-run the query with the Pricing chart in view.
  - **Role:** ingested as Step 0b. It fills ONLY the fields that method-2 (#1A) did not capture. Method-2 is the superset, and it wins on overlap.

### 2. Artificial Analysis — live API (`aa_api_live.json`)
- **Method:** `GET https://artificialanalysis.ai/api/v2/data/llms/models` with header `x-api-key: ***`
- **Auth:** free-tier key (100 req/day). Key stored in Hermes `.env` as `AA_API_KEY` — **never hardcode**.
- **Payload:** `status`, `prompt_options`, `data[]` (671 models). Each has `slug`, `release_date`, `model_creator.name`, `evaluations{}` (16 scores: hle, gpqa, aime, aime_25, scicode, lcr, terminalbench_v2_1, …).
- **Repro:**
  ```bash
  curl -s -H "x-api-key: ${AA_API_KEY}" https://artificialanalysis.ai/api/v2/data/llms/models \
    | python -m json.tool > data/sources/aa/aa_api_live.json
  ```
- **Used for:** `release_date`, `creator` backfill, 16 live-AA benchmark axes.

### 2A. Artificial Analysis — public model catalog (`aa_public_model_catalog.json`)
- **Method:** `_pull_sources.py` requests the public providers page as a Next.js React Server Components (RSC) payload. It needs no API key and returns model variants with `release.slug`, `release.name`, `releaseDate`, and `creator.name`.
- **File:** `data/sources/aa/aa_public_model_catalog.json` (671 variants, fetched 2026-09-24).
- **Role:** fills creator, release date, and official model-family metadata for existing AA models only. It does not seed models or add benchmark metrics. The family value is `{slug, name}` from the AA `release` field. The RSC route is an internal website payload, not a stable public API. The keyed REST API remains authoritative for evaluation scores.
- **Repro:** `PYTHONPATH=data python -m data._pull_sources`.

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

### 7. Dirac.run (`dirac/cache_hit_rates.json` → `dirac/provider_rates.json`)
- **Method:** fetch `dirac.run/posts/cache-hit-rates-agents`, then parse the `#the-full-table` `<table>`. The page renders the full table in HTML, so extract the `<tr>` rows → `model`, `provider`, `eff_input_price`, `eff_output_price`, `cache_hit_rate`. **Automated:** `data/sources/dirac/_fetch.py` (`pull_dirac`) runs as part of `_pull_sources`. It fetches, parses, writes the raw table, and rebuilds the provider artifact. No manual transcription.
- **403 pitfall:** dirac.run rejects the default `urllib` User-Agent. `_fetch.py` sends a browser UA.
- **No API.** 398 rows: `model`, `provider`, `cache_hit_rate`, `eff_input_price`, `eff_output_price`.
- **Semantics:** observed % of input served from prefix cache — distinct from AA's `cache_hit_price` ($/Mtok read price). Never conflate. `eff_input_price` / `eff_output_price` are observed *effective* $/M (cache effect already blended in).
- **Provider-centric artifact:** `dirac/provider_rates.json` = `{provider: [{slug, model_name, cache_hit_rate, eff_input_price, eff_output_price}]}`, sorted by provider coverage then per-provider hit rate. This is the provider→model mapping the dashboard toggles on.
- **Repro:** `PYTHONPATH=data python -m data._pull_sources` (fetches the table and rebuilds the provider artifact). Offline rebuild of just the provider artifact from the committed table: `PYTHONPATH=data python -m data.sources.dirac._build_provider_rates`.
- **Id resolution happens at registry time, in code — not in the file.** `data/sources/dirac/_build.py` resolves each `model_name` through `DIRAC_NAME_MAP` (`data/_canonical.py`), then falls back to the `slug` in the file. `step_dirac` attaches the record **only to a model that already exists**: an exact id, or a unique dot/dash-normalized match. It counts the rest as unresolved, and it never invents a record. A stale map target used to create a nameless shell model next to the real one. 57 of 74 provider-mapped models were such shells, and `glm-5.1` had its provider rows split 19+6 across both ids.

### 8. Chatbot Arena (Code + Text)
- **Method:** **manual JSON download** of the leaderboard → `arena_code.json` / `arena_text.json` (each has `meta` + `models[]`).
- **Not fetched by any script.** Place the files manually. `_build_registry.py` consumes them.

### 9. misc.json (context-window overlay)
- **Method:** hand-written JSON — `{slug: {context_window: int}}`, 43 entries.
- **Consumed by:** `step_misc` in `_build_registry.py` fills `meta.context_window` only where the field is absent or null (an OpenRouter `context_length` wins on overlap).
- **Not fetched by any script.** Edit in place when a model's context window is missing from OpenRouter.

## What `_pull_sources.py` actually covers
**#2A AA public catalog, #3 OpenRouter, #5 LiveBench, and #7 Dirac.run** are fetched by the script. The script also processes the manually downloaded #6 OpenLLM v2 parquet file. You acquire the other sources (#1, #1A, #1B, #2, #8) **manually**: scrape, console-query, keyed API pull, or JSON download. Then commit them as files. #9 is hand-maintained.

> **AA is ONE unified source, not separate streams.** Scraped (#1), SVG scrape (#1A), JSON-LD console-query (#1B), live API (#2), and the public catalog (#2A) all feed `get_aa_models()`. Only charts and JSON-LD seed the model set. API and catalog metadata attaches to those models, and it never adds new ones.

### Refresh status (`_pull_status.json`)

`_pull_sources.py` writes `data/sources/_pull_status.json` on every run, before it decides the stage outcome. The file records `checked_at`, the sources that refreshed (`ok`), and the sources that failed (`failed`, with the error text).

A failed refresh leaves the previous source file in place, so the build still succeeds. `_build_registry._source_meta()` reads this file and marks the affected source `refresh_failed` in `source_meta`. That flag flows into `processed.js` (`sources_meta`). The dashboard marks the source in the footer and in the provenance note of each affected chart.

Commit the file with the sources. The offline build reads it, so the warning stays on the artifact until a refresh succeeds.

## Repro checklist (full refresh)

```bash
# Manual (outside script):
#  - run external AA scraper → aa/raw + aa/enriched
#  - copy aa_charts_export.json (SVG console scrape of AA page) → aa/      (PRIMARY)
#  - copy aa_jsonld_export.json (JSON-LD console query of AA page) → aa/  (fills gaps)
#  - pull AA live API → aa/aa_api_live.json   (needs AA_API_KEY)
#  - download Arena JSON → arena_code.json, arena_text.json
#  - download openllm_v2.parquet → data/sources/
#  - bump UNDATED_SNAPSHOTS in data/_build_registry.py to the new snapshot dates

# Full build (network pull of OpenRouter/LiveBench/OpenLLM/Dirac.run, then registry → axes → dashboard):
python -m data._pipeline            # no arg → build() pulls + builds

# Offline rebuild (uses committed sources, no network):
python -m data._pipeline build      # or: build_from_cache
```

`_pull_sources.py` itself (with no arg) fetches the public AA catalog, OpenRouter, LiveBench, OpenLLM v2, and Dirac.run. The manual sources above are committed files. `_build_registry` consumes them regardless of the pull.
