import json, os
from pathlib import Path

from ..._canonical import dirac_name_to_canonical


def get_dirac_models(base: Path) -> dict[str, dict]:
    """Dirac.run observed cache hit rates → canonical_id → record.

    Reads from provider_rates.json (provider-centric) and derives the per-model
    cache_hit_rate_max axis (max across all providers for that model).

    Source: dirac.run/posts/cache-hit-rates-agents#the-full-table
    (OpenRouter "Effective Pricing" hourly snapshots, 398 data points).
    Cache hit rate is the OBSERVED % of input tokens served from prefix cache —
    semantically distinct from AA's cache_hit_price ($/Mtok read price).

    The provider_rates.json file is built by _build_provider_rates.py from the
    raw cache_hit_rates.json. It is a dict {provider: [entries]} where each
    entry has slug, model_name, cache_hit_rate, eff_input_price, eff_output_price.
    """
    provider_path = os.path.join(base, "data", "sources", "dirac", "provider_rates.json")
    if not os.path.exists(provider_path):
        raw_path = os.path.join(base, "data", "sources", "dirac", "cache_hit_rates.json")
        if not os.path.exists(raw_path):
            return {}
        return _from_raw(raw_path)

    with open(provider_path) as f:
        provider_data = json.load(f)

    out: dict[str, dict] = {}
    for provider, entries in provider_data.items():
        for entry in entries:
            slug = entry.get("slug")
            if not slug:
                continue
            rec = out.setdefault(slug, {
                "benchmarks": {"dirac": {}},
                "meta": {"dirac_cache_hit_rates": []},
            })
            rec["meta"]["dirac_cache_hit_rates"].append({
                "provider": provider,
                "cache_hit_rate": entry.get("cache_hit_rate"),
                "eff_input_price": entry.get("eff_input_price"),
                "eff_output_price": entry.get("eff_output_price"),
            })

    for cid, rec in out.items():
        rates = [x["cache_hit_rate"] for x in rec["meta"]["dirac_cache_hit_rates"]
                 if x["cache_hit_rate"] is not None]
        if rates:
            rec["benchmarks"]["dirac"]["cache_hit_rate_max"] = max(rates)

    return out


def _from_raw(raw_path: str) -> dict[str, dict]:
    """Legacy path: read raw cache_hit_rates.json directly."""
    with open(raw_path) as f:
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
