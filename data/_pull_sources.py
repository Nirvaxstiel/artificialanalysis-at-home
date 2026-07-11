import json, csv, io, os, sys, urllib.request
from pathlib import Path

from _result import ok, err, from_fn


def _src_dir(ctx):
    base = str(ctx["root"]) if (ctx and ctx.get("root")) else str(Path(__file__).resolve().parent.parent)
    src = os.path.join(base, "data", "sources")
    os.makedirs(src, exist_ok=True)
    return src


def pull_livebench(src):
    """Fetch LiveBench table + categories. Returns Ok(dict) or Err(reason)."""
    lb_url = "https://raw.githubusercontent.com/LiveBench/livebench.github.io/main/public/table_2026_01_08.csv"
    try:
        urllib.request.urlretrieve(lb_url, os.path.join(src, "livebench_2026_01_08.csv"))
    except Exception as e:  # noqa: BLE001 — network/IO failure is a Result, not a crash
        return err(f"livebench table: {e}")

    cat_url = "https://raw.githubusercontent.com/LiveBench/livebench.github.io/main/public/categories_2026_01_08.json"
    try:
        urllib.request.urlretrieve(cat_url, os.path.join(src, "livebench_categories_2026_01_08.json"))
    except Exception as e:  # noqa: BLE001
        return err(f"livebench categories: {e}")

    try:
        with open(os.path.join(src, "livebench_2026_01_08.csv"), "r") as f:
            reader = csv.reader(f)
            header = next(reader)
        with open(os.path.join(src, "livebench_categories_2026_01_08.json"), "r") as f:
            cats = json.load(f)
    except Exception as e:  # noqa: BLE001
        return err(f"livebench parse: {e}")

    return ok({"csv": "livebench_2026_01_08.csv", "json": "livebench_categories_2026_01_08.json",
               "columns": len(header), "categories": list(cats.keys())})


def pull_openllm(src):
    """Read the OpenLLM v2 parquet, emit the AA-relevant subset. Ok(dict) or Err(reason)."""
    try:
        import pyarrow.parquet as pq
        table = pq.read_table(os.path.join(src, "openllm_v2.parquet"))
    except Exception as e:  # noqa: BLE001
        return err(f"openllm parquet: {e}")

    try:
        cols = table.schema.names
        aa_keywords = ["gpt-5", "deepseek", "gemini", "claude", "llama", "qwen", "mistral", "grok", "minimax", "glm"]
        aa_rows = []
        for i in range(len(table)):
            model = table.column("Model")[i].as_py() or ""
            if any(k in model.lower() for k in aa_keywords):
                row = {c: v for c in cols if (v := table.column(c)[i].as_py()) is not None}
                aa_rows.append(row)
        with open(os.path.join(src, "openllm_aa_subset.json"), "w") as f:
            json.dump(aa_rows, f, indent=2, default=str)
    except Exception as e:  # noqa: BLE001
        return err(f"openllm subset: {e}")

    return ok({"json": "openllm_aa_subset.json", "rows": len(aa_rows)})


def pull_openrouter(src):
    """Fetch the OpenRouter models API, normalize pricing. Ok(dict) or Err(reason)."""
    or_url = "https://openrouter.ai/api/v1/models"
    try:
        resp = urllib.request.urlopen(or_url)
        or_data = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        return err(f"openrouter fetch: {e}")

    try:
        items = or_data.get("data", [])
        fetched_models = []
        for model in items:
            provider_id = model["id"]
            pricing = model.get("pricing", {})
            fetched_models.append({
                "id": provider_id,
                "name": model.get("name", provider_id),
                "vendor": provider_id.split("/")[0] if "/" in provider_id else "",
                "input_price": pricing.get("prompt"),
                "output_price": pricing.get("completion"),
                "cache_read_price": pricing.get("input_cache_read"),
                "cache_write_price": pricing.get("input_cache_write"),
                "context_length": model.get("context_length"),
            })
        with open(os.path.join(src, "openrouter_models.json"), "w") as f:
            json.dump(fetched_models, f, indent=2)
    except Exception as e:  # noqa: BLE001
        return err(f"openrouter normalize: {e}")

    return ok({"json": "openrouter_models.json", "models": len(fetched_models)})


def run(ctx=None):
    src = _src_dir(ctx)

    sources = {
        "livebench": pull_livebench(src),
        "openllm": pull_openllm(src),
        "openrouter": pull_openrouter(src),
    }

    ok_sources = [n for n, r in sources.items() if r.is_ok()]
    failed = {n: r.error for n, r in sources.items() if r.is_err()}

    files = sorted(os.listdir(src))
    summary = {"src_dir": src, "files": files, "ok_sources": ok_sources, "failed_sources": failed}

    if not ok_sources:
        return err(f"all sources failed: {failed}")
    return ok(summary)


if __name__ == "__main__":
    result = run()
    if result.is_err():
        print("PULL FAILED:", result.error)
        sys.exit(1)
    pipeline_state = result.unwrap()
    print("=" * 60)
    print("DATA COLLECTION COMPLETE")
    print("=" * 60)
    print(f"\nFiles in {s['src_dir']}:")
    for f in s["files"]:
        print(f"  {f:45s} {os.path.getsize(os.path.join(s['src_dir'], f)):>8,} bytes")
    if s["failed_sources"]:
        print(f"\nFailed sources: {s['failed_sources']}")
