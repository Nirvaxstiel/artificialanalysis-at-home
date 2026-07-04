"""Read OpenLLM Leaderboard v2 parquet and dump schema + sample."""
import json, os

base = r"C:\Users\Kei\.obsidian\Vault\KeiUniverse\IRL\Reference\LLM Provider Pricing Analysis"
sources = os.path.join(base, "data", "sources")

try:
    import pyarrow.parquet as pq
    HAVE_PARQUET = True
except ImportError:
    HAVE_PARQUET = False

if HAVE_PARQUET:
    pf = os.path.join(sources, "openllm_v2.parquet")
    table = pq.read_table(pf)
    cols = table.schema.names
    print("COLUMNS:", cols)
    print("ROWS:", len(table))
    
    # First 5 rows as dicts
    pdf = table.to_pandas()
    print("\n=== FIRST 5 ROWS ===")
    for i, row in pdf.head(5).iterrows():
        print(f"\nRow {i}:")
        for c in cols:
            v = row[c]
            if v is not None and v == v:  # not NaN
                print(f"  {c}: {v}")
    
    # Extract AA-relevant model names
    print("\n=== AA MODELS IN DATASET ===")
    aa_slugs = ["gpt-5-5", "gpt-5-4", "deepseek", "gemini", "claude", "llama", "qwen", "mistral", "grok", "minimax", "glm"]
    for i, row in pdf.head(50).iterrows():
        model = str(row.get("model", ""))
        if any(s in model.lower() for s in aa_slugs):
            vals = {c: row[c] for c in cols if row[c] is not None and c != "model"}
            print(f"\n  {model}")
            for k, v in vals.items():
                print(f"    {k}: {v}")
else:
    print("pyarrow not available. Use: python -m pip install pyarrow")
