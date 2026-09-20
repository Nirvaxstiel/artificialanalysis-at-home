import json, re, urllib.request
from pathlib import Path

from _result import ok, err

from sources.dirac._build_provider_rates import build_provider_rates

TABLE_URL = "https://dirac.run/posts/cache-hit-rates-agents"
TABLE_ANCHOR = 'id="the-full-table"'
HEADER_FIRST_CELL = "Model Name"
USER_AGENT = "Mozilla/5.0 (compatible; artificialanalysis-at-home/1.0)"


def _cell_text(cell_html):
    return re.sub(r"<[^>]+>", "", cell_html).strip()


def _money(text):
    return float(text.replace("$", "").replace(",", "")) if text else None


def _percent(text):
    return float(text.rstrip("%")) if text else None


def parse_cache_table(html):
    anchor = html.find(TABLE_ANCHOR)
    if anchor < 0:
        return err("dirac: #the-full-table anchor not found")
    start = html.find("<table", anchor)
    end = html.find("</table>", start)
    if start < 0 or end < 0:
        return err("dirac: full table element not found")

    rows = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html[start:end], re.S):
        cells = [_cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)]
        if len(cells) < 5 or cells[0] == HEADER_FIRST_CELL:
            continue
        rows.append({
            "model": cells[0],
            "provider": cells[1],
            "eff_input_price": _money(cells[2]),
            "eff_output_price": _money(cells[3]),
            "cache_hit_rate": _percent(cells[4]),
        })
    return ok(rows)


def pull_dirac(src):
    try:
        request = urllib.request.Request(TABLE_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 — network failure is a Result, not a crash
        return err(f"dirac fetch: {e}")

    parsed = parse_cache_table(html)
    if parsed.is_err():
        return parsed
    rows = parsed.unwrap()
    if not rows:
        return err("dirac: parsed 0 rows")

    out_dir = Path(src, "dirac")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "cache_hit_rates.json"
    raw_path.write_text(json.dumps(rows, indent=2))

    try:
        build_provider_rates(raw_path, out_dir / "provider_rates.json")
    except (OSError, ValueError, KeyError) as e:  # noqa: BLE001
        return err(f"dirac provider rates: {e}")

    return ok({"rows": len(rows), "providers": len({r["provider"] for r in rows})})
