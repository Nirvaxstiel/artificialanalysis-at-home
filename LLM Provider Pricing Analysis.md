# LLM Provider Pricing Analysis

**Source:** Artificial Analysis — Intelligence Index v4.1 (3 Jul '26)
**Data:** 38 models, scraped + vision-extracted from charts

## Files

- `data/aa_model_data.json` — full structured dataset (all metrics, derived)
- `data/aa_model_data.csv` — same data as CSV
- `data/aa_cost_breakdown.json` — per-task cost segmented by token type (Answer / Reasoning / Cache Write / Cache Hit / Input) — **from vision-extracted bar chart**

## Crossover Visualizations To Build (Future)

| Combo | What It Shows |
|---|---|
| Intelligence × Cost per Task | Pareto frontier — which models hit highest IQ for least $? |
| Intelligence × Output Tokens per Task | Token efficiency — who produces least tokens? |
| Cost per Task × Tokens per Task | Bubble = IQ. Reveals "talkative but cheap" vs "concise but expensive" |
| Reasoning % of tokens × Cost | Why "low thinking" models look cheap on $/token |
| Provider aggregates | Avg IQ, avg cost, avg tokens per org |

## Datasets

### Primary (`aa_model_data.csv` / `.json`)

Fields: slug, name, creator, type, intelligence_index, total_cost_usd, total_output_tokens_m, input_price_per_m, output_price_per_m, cache_hit_price_per_m, blended_price_per_m, speed_tokens_per_sec, cost_per_iq_point, iq_per_1000_dollars, tokens_m_per_iq, effective_cost_per_m_output

### Cost Breakdown (`aa_cost_breakdown.json`)

Per-task cost in USD, segmented by token type (Answer, Reasoning, Cache Write, Cache Hit, Input). Bar chart total values read directly from labels; segments estimated by color ratio.

## Key Findings

**Token efficiency ≠ Cost efficiency.** Frontier proprietary models are concise but expensive. DeepSeek/MiniMax are verbose but cheap.

**Reasoning vs Answer split is the new axis.** Reasoning tokens are priced at output rate. A "reasoning" model that spends 80% of its output tokens thinking will pay 80% × output_price just for thinking.

**The MiniMax sweet spot:** M3 sits in the green quadrant (low cost, mid IQ, mid tokens).

## Charts (Reference)

![[AA Charts/Intelligence vs- Cost per Intelligence Index Task (3 Jul '26).png]]
![[AA Charts/Intelligence vs- Output Tokens Used in Artificial Analysis Intelligence Index (3 Jul '26).png]]
![[AA Charts/Cost per Intelligence Index Task (3 Jul '26).png]]
![[AA Charts/Output Tokens per Intelligence Index Task (3 Jul '26).png]]
![[AA Charts/Intelligence vs- Output Tokens per Intelligence Index Task (3 Jul '26).png]]
![[AA Charts/Intelligence vs- Output Speed (3 Jul '26).png]]
![[AA Charts/Intelligence vs- Time per Intelligence Index Task (3 Jul '26).png]]
![[AA Charts/Intelligence vs- End-to-End Response Time (3 Jul '26).png]]
![[AA Charts/Intelligence vs- Context Window (3 Jul '26).png]]
![[AA Charts/Intelligence Evaluations (3 Jul '26).png]]
![[AA Charts/Evaluation Breakdown (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Intelligence Index (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Coding Index (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Agentic Index (3 Jul '26).png]]
![[AA Charts/AA-Omniscience Index (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Openness Index - Score (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Openness Index - Components (3 Jul '26).png]]
![[AA Charts/Artificial Analysis Openness Index vs- Artificial Analysis Intelligence Index (3 Jul '26).png]]
![[AA Charts/Context Window (3 Jul '26).png]]

## Methodology

AA Intelligence Index v4.1 (9 weighted evals): GDPval-AA v2, τ³-Banking, Terminal-Bench v2.1, SciCode, HLE, GPQA Diamond, CritPt, AA-Omniscience, AA-LCR.

Cost per Task = (input×input_price + cache_hit×cache_hit_price + cache_write×cache_write_price + reasoning×output_price + answer×output_price) / task_count, weighted by eval importance. Uses measured per-model per-eval token counts.
