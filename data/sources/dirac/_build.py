import json, os
from pathlib import Path

from ..._canonical import dirac_name_to_canonical


def resolve_dirac_id(entry: dict) -> str | None:
    mapped = dirac_name_to_canonical(entry.get("model_name") or "").unwrap_or(None)
    return mapped or entry.get("slug") or None


def get_dirac_models(base: Path) -> dict[str, dict]:
    provider_path = os.path.join(base, "data", "sources", "dirac", "provider_rates.json")
    if not os.path.exists(provider_path):
        return {}

    with open(provider_path) as f:
        provider_data = json.load(f)

    out: dict[str, dict] = {}
    for provider, entries in provider_data.items():
        for entry in entries:
            canonical_id = resolve_dirac_id(entry)
            if not canonical_id:
                continue
            record = out.setdefault(canonical_id, {
                "benchmarks": {"dirac": {}},
                "meta": {"dirac_cache_hit_rates": []},
            })
            record["meta"]["dirac_cache_hit_rates"].append({
                "provider": provider,
                "cache_hit_rate": entry.get("cache_hit_rate"),
                "eff_input_price": entry.get("eff_input_price"),
                "eff_output_price": entry.get("eff_output_price"),
            })

    for record in out.values():
        rates = [r["cache_hit_rate"] for r in record["meta"]["dirac_cache_hit_rates"]
                 if r["cache_hit_rate"] is not None]
        if rates:
            record["benchmarks"]["dirac"]["cache_hit_rate_max"] = max(rates)

    return out