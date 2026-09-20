#!/usr/bin/env python3
"""Build provider-centric cache hit rate data from Dirac.raw.

Output: data/sources/dirac/provider_rates.json
  {provider: {models: [{slug, model_name, cache_hit_rate, eff_input_price, eff_output_price}, ...], ...}}

Also writes a summary stats file for the build pipeline to consume.
"""
import json
import os
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_json(path: str):
    with open(path) as f:
        return json.load(f)


def build_provider_rates():
    raw_path = BASE / "data" / "sources" / "dirac" / "cache_hit_rates.json"
    if not raw_path.exists():
        return {}

    rows = _load_json(str(raw_path))

    by_provider: dict[str, list] = defaultdict(list)
    for r in rows:
        by_provider[r["provider"]].append({
            "model_name": r["model"],
            "cache_hit_rate": r["cache_hit_rate"],
            "eff_input_price": r["eff_input_price"],
            "eff_output_price": r["eff_output_price"],
        })

    # Sort models within each provider by cache_hit_rate descending
    for prov in by_provider:
        by_provider[prov].sort(key=lambda m: -(m["cache_hit_rate"] or 0))

    # Sort providers by model count descending
    sorted_provs = dict(
        sorted(by_provider.items(), key=lambda x: -len(x[1]))
    )

    out_path = BASE / "data" / "sources" / "dirac" / "provider_rates.json"
    with open(out_path, "w") as f:
        json.dump(sorted_provs, f, indent=2)

    print(f"Written {len(sorted_provs)} providers, "
          f"{sum(len(v) for v in sorted_provs.values())} model-entries "
          f"to {out_path.name}")
    return sorted_provs


if __name__ == "__main__":
    build_provider_rates()
