import json, os
from pathlib import Path

from ..._canonical import dirac_name_to_canonical


def get_dirac_models(base: Path) -> dict[str, dict]:
    """Dirac.run observed cache hit rates → canonical_id → record.

    Source: dirac.run/posts/cache-hit-rates-agents#the-full-table
    (OpenRouter "Effective Pricing" hourly snapshots, 398 data points).
    Cache hit rate is the OBSERVED % of input tokens served from prefix cache —
    semantically distinct from AA's cache_hit_price ($/Mtok read price).

    Each canonical model may have several provider observations. We expose the
    max observed rate (the achievable ceiling for an agentic workload) as the
    primary axis, and carry the per-provider rows for the UI tooltip.
    """
    path = os.path.join(base, "data", "sources", "dirac", "cache_hit_rates.json")
    if not os.path.exists(path):
        return {}

    with open(path) as f:
        rows = json.load(f)

    out: dict[str, dict] = {}
    for r in rows:
        cid = dirac_name_to_canonical(r.get("model", "")).unwrap_or(None)
        if not cid:
            continue
        rec = out.setdefault(cid, {
            "benchmarks": {"dirac": {}},
            "meta": {"dirac_cache_hit_rates": []},
        })
        rec["meta"]["dirac_cache_hit_rates"].append({
            "provider": r.get("provider"),
            "cache_hit_rate": r.get("cache_hit_rate"),
            "eff_input_price": r.get("eff_input_price"),
            "eff_output_price": r.get("eff_output_price"),
        })

    for cid, rec in out.items():
        rates = [x["cache_hit_rate"] for x in rec["meta"]["dirac_cache_hit_rates"]
                 if x["cache_hit_rate"] is not None]
        if rates:
            rec["benchmarks"]["dirac"]["cache_hit_rate_max"] = max(rates)

    return out
