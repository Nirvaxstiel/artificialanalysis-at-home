"""Pull all open-source benchmarking data into data/sources/"""
import json, csv, io, os, sys, urllib.request

base = r"C:\Users\Kei\.obsidian\Vault\KeiUniverse\IRL\Reference\LLM Provider Pricing Analysis"
src = os.path.join(base, "data", "sources")
os.makedirs(src, exist_ok=True)

# ── LIVERBENCH ──
print("=== LIVERBENCH ===")
# Latest table CSV
lb_url = "https://raw.githubusercontent.com/LiveBench/livebench.github.io/main/public/table_2026_01_08.csv"
urllib.request.urlretrieve(lb_url, os.path.join(src, "livebench_2026_01_08.csv"))
print("  table_2026_01_08.csv saved")

# Categories
cat_url = "https://raw.githubusercontent.com/LiveBench/livebench.github.io/main/public/categories_2026_01_08.json"
try:
    urllib.request.urlretrieve(cat_url, os.path.join(src, "livebench_categories_2026_01_08.json"))
    print("  categories saved")
except:
    print("  categories not found")

# Show header
with open(os.path.join(src, "livebench_2026_01_08.csv"), "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"  Columns ({len(header)}): {header}")
    for i, row in enumerate(reader):
        if i < 3:
            print(f"  Row {i}: {row[:8]}...")
        else:
            break

with open(os.path.join(src, "livebench_categories_2026_01_08.json"), "r") as f:
    cats = json.load(f)
    print(f"  Categories: {list(cats.keys())}")

# ── OPEN LLM v2 ──
print("\n=== OPEN LLM v2 ===")
import pyarrow.parquet as pq
table = pq.read_table(os.path.join(src, "openllm_v2.parquet"))
cols = table.schema.names
print(f"  Columns ({len(cols)}): {cols}")
print(f"  Rows: {len(table)}")

# Sample rows for AA-related models (pure pyarrow — no pandas)
aa_keywords = ["gpt-5", "deepseek", "gemini", "claude", "llama", "qwen", "mistral", "grok", "minimax", "glm"]
print("\n  AA-relevant model rows (first 10):")
found = 0
for i in range(len(table)):
    model = table.column("Model")[i].as_py() or ""
    model_lower = model.lower()
    if any(k in model_lower for k in aa_keywords):
        if found < 10:
            print(f"  {model}")
            for c in cols:
                v = table.column(c)[i].as_py()
                if v is not None:
                    print(f"    {c}: {v}")
            print()
            found += 1
        else:
            break

# Save AA-relevant subset to JSON
aa_rows = []
for i in range(len(table)):
    model = table.column("Model")[i].as_py() or ""
    model_lower = model.lower()
    if any(k in model_lower for k in aa_keywords):
        row = {}
        for c in cols:
            v = table.column(c)[i].as_py()
            if v is not None:
                row[c] = v
        aa_rows.append(row)

with open(os.path.join(src, "openllm_aa_subset.json"), "w") as f:
    json.dump(aa_rows, f, indent=2, default=str)
print(f"  Saved {len(aa_rows)} AA-relevant models to openllm_aa_subset.json")

# ── OPENROUTER ──
print("\n=== OPENROUTER ===")
or_url = "https://openrouter.ai/api/v1/models"
resp = urllib.request.urlopen(or_url)
or_data = json.loads(resp.read())
items = or_data.get("data", [])
print(f"  Total models: {len(items)}")

# Filter to models with pricing + cache data
cache_models = [m for m in items if m.get("pricing", {}).get("input_cache_read")]
print(f"  Models with cache pricing: {len(cache_models)}")

# Extract key fields
out = []
for m in items:
    pid = m["id"]
    pr = m.get("pricing", {})
    out.append({
        "id": pid,
        "name": m.get("name", pid),
        "vendor": pid.split("/")[0] if "/" in pid else "",
        "input_price": pr.get("prompt"),
        "output_price": pr.get("completion"),
        "cache_read_price": pr.get("input_cache_read"),
        "cache_write_price": pr.get("input_cache_write"),
    })

with open(os.path.join(src, "openrouter_models.json"), "w") as f:
    json.dump(out, f, indent=2)
print(f"  Saved {len(out)} models to openrouter_models.json")

# ── SUMMARY ──
print("\n" + "="*60)
print("DATA COLLECTION COMPLETE")
print("="*60)
print(f"\nFiles in {src}:")
for f in sorted(os.listdir(src)):
    sz = os.path.getsize(os.path.join(src, f))
    print(f"  {f:45s} {sz:>8,} bytes")
