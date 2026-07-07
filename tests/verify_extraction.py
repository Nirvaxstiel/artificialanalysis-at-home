"""Verify HTML extraction fidelity and analyze aa.intel coverage."""
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
print(f"=== VERIFICATION: HTML extraction fidelity ===")

# 1. Extract inline data from old (committed) dashboard.html
old_html = (REPO / "dashboard.html").read_text()
m = re.search(r'window\.PROCESSED_DATA = (\[.*?\]);', old_html, re.DOTALL)
if not m:
    # Try reading from git HEAD
    import subprocess
    r = subprocess.run(["git", "show", "HEAD:dashboard.html"], capture_output=True, text=True, cwd=REPO)
    old_html = r.stdout
    m = re.search(r'window\.PROCESSED_DATA = (\[.*?\]);', old_html, re.DOTALL)

old_data = json.loads(m.group(1))
print(f"Inline data models: {len(old_data)}")

# 2. Field inventory
all_fields = set()
for mo in old_data:
    all_fields.update(mo.keys())
print(f"Unique fields ({len(all_fields)}):")
for f in sorted(all_fields):
    # Check types
    vals = [mo.get(f) for mo in old_data if f in mo]
    non_null = [v for v in vals if v is not None]
    types = set(type(v).__name__ for v in non_null)
    print(f"  {f}: null={len(vals)-len(non_null)}/{len(vals)}  types={types}")

# 3. Check processed.js matches inline data
js_path = REPO / "data" / "processed.js"
js_content = js_path.read_text()
m_js = re.match(r'window\.PROCESSED_DATA\s*=\s*(\[.*?\]);', js_content, re.DOTALL)
js_data = json.loads(m_js.group(1))
print(f"\nprocessed.js models: {len(js_data)}")

# Compare slug-by-slug
old_map = {m["slug"]: m for m in old_data}
js_map = {m["slug"]: m for m in js_data}

missing_in_js = set(old_map.keys()) - set(js_map.keys())
extra_in_js = set(js_map.keys()) - set(old_map.keys())
print(f"Slugs missing from processed.js: {len(missing_in_js)}")
for s in sorted(missing_in_js)[:5]:
    print(f"  Missing: {s}")
print(f"Extra slugs in processed.js: {len(extra_in_js)}")
for s in sorted(extra_in_js)[:5]:
    print(f"  Extra: {s}")

# Field-level comparison
if not missing_in_js and not extra_in_js:
    diffs = []
    for slug in old_map:
        if slug in js_map:
            o = old_map[slug]
            j = js_map[slug]
            for k in set(list(o.keys()) + list(j.keys())):
                if o.get(k) != j.get(k):
                    diffs.append((slug, k, o.get(k), j.get(k)))
    print(f"\nField-level diffs: {len(diffs)}")
    for slug, k, ov, jv in diffs[:10]:
        print(f"  {slug}.{k}: old={ov!r} js={jv!r}")

# 4. Analyze aa.intel coverage
print(f"\n=== AA.INTEL ANALYSIS ===")
with_intel = [m for m in old_data if m.get("intel") is not None]
without_intel = [m for m in old_data if m.get("intel") is None]
print(f"Models with intel: {len(with_intel)}")
print(f"Models without intel: {len(without_intel)}")

# What do the no-intel models have?
for m in without_intel:
    non_null = {k: v for k, v in m.items() if v is not None}
    print(f"  {m['slug']}: {len(non_null)} non-null fields: {list(non_null.keys())[:8]}...")

# Check against current registry
reg = json.load(open(REPO / "data" / "model_registry.json"))
reg_map = {m["id"]: m for m in reg["models"]}
in_registry = [s for s in old_map if s in reg_map]
not_in_registry = [s for s in old_map if s not in reg_map]
print(f"\nOld slugs still in registry: {len(in_registry)}")
print(f"Old slugs gone from registry: {len(not_in_registry)}")

# For old slugs in registry, do they have aa.intel in the registry?
for s in in_registry[:5]:
    rm = reg_map[s]
    r_intel = rm.get("benchmarks", {}).get("aa", {}).get("intel")
    r_inp = rm.get("pricing", {}).get("aa", {}).get("inp_price_m")
    print(f"  {s}: old.intel={old_map[s].get('intel')!r}, reg.intel={r_intel!r}, reg.inp_price={r_inp!r}")
