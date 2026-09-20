#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

from _canonical import dirac_name_to_canonical

HERE = Path(__file__).resolve().parent
RAW_PATH = HERE / "cache_hit_rates.json"
OUT_PATH = HERE / "provider_rates.json"


def build_provider_rates(raw_path=RAW_PATH, out_path=OUT_PATH):
    if not Path(raw_path).exists():
        print(f"missing {Path(raw_path).name} — nothing to build")
        return {}

    rows = json.loads(Path(raw_path).read_text())

    by_provider: dict[str, list] = defaultdict(list)
    unresolved = set()
    for row in rows:
        canonical_id = dirac_name_to_canonical(row["model"]).unwrap_or(None)
        if not canonical_id:
            unresolved.add(row["model"])
            continue
        by_provider[row["provider"]].append({
            "slug": canonical_id,
            "model_name": row["model"],
            "cache_hit_rate": row["cache_hit_rate"],
            "eff_input_price": row["eff_input_price"],
            "eff_output_price": row["eff_output_price"],
        })

    for entries in by_provider.values():
        entries.sort(key=lambda e: -(e["cache_hit_rate"] or 0))

    ordered = dict(sorted(by_provider.items(), key=lambda item: -len(item[1])))
    Path(out_path).write_text(json.dumps(ordered, indent=2))

    entries_total = sum(len(v) for v in ordered.values())
    print(f"{Path(out_path).name}: {len(ordered)} providers, {entries_total} model-entries, "
          f"{len(unresolved)} dirac names unresolved by the canonical map")
    for name in sorted(unresolved):
        print(f"  unresolved: {name}")
    return ordered


if __name__ == "__main__":
    build_provider_rates()