import json
import os
import re
from pathlib import Path


CHART_MAP = {
    0: "coding_index",
    1: "intel",
    2: "briefcase",
    3: "omniscience",
    8: "cost_to_run",
    9: "pricing",
    12: "time_per_task",
}


def _norm_value(text: str):
    """Parse a chart label into a float. Handles 78.3, $470, 16%, &lt;0.01, <0.01.

    Percent values (only the Omniscience chart uses %) are returned as a
    fraction (16% -> 0.16), matching the 0..1 schema of omniscience_hallucination_rate.
    """
    t = text.strip()
    t = t.replace("&lt;", "<").replace("&gt;", ">")
    is_pct = "%" in t
    t = t.replace("$", "").replace("%", "").replace(",", "")
    m = re.match(r"^<?\s*([\d.]+)$", t)
    if not m:
        return None
    val = float(m.group(1))
    if t.startswith("<"):
        val = -val  # sentinel: store magnitude, flag "less than" upstream if needed
    if is_pct:
        val = val / 100.0
    return val


def _extract_slugs(svg: str):
    """All model slugs in render order (from <a href='/models/{slug}'>)."""
    return re.findall(r'href="/models/([a-z0-9\-]+)"', svg)


def _extract_values(svg: str):
    """All numeric-ish label values in render order (from <text> nodes)."""
    texts = re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)
    out = []
    for t in texts:
        inner = re.sub(r"<[^>]+>", "", t).strip()
        if not inner:
            continue
        if re.search(r"[\d]", inner) and not re.search(r"[A-Za-z]", inner.replace("%", "").replace("$", "").replace("<", "").replace(",", "").replace(".", "")):
            v = _norm_value(inner)
            if v is not None:
                out.append(v)
    return out


def _parse_chart(svg: str):
    """Return list of (slug, value) or (slug, [v1, v2, ...]).

    Single-value charts → (slug, float). Multi-value charts (ratio N:M with N<M)
    → (slug, [floats]).
    """
    slugs = _extract_slugs(svg)
    vals = _extract_values(svg)
    if not slugs:
        return []
    if len(vals) == len(slugs):
        return list(zip(slugs, vals))
    if len(vals) > len(slugs) and len(vals) % len(slugs) == 0:
        per = len(vals) // len(slugs)
        return [(slugs[i], vals[i * per:(i + 1) * per]) for i in range(len(slugs))]
    # Ambiguous: fall back to zip (best-effort)
    return list(zip(slugs, vals))


def parse_aa_charts(json_path: str) -> dict[str, list]:
    """Parse the method-2 SVG scrape → {chart_key: [(slug, value), ...]}.

    Only the 7 ranking/bar charts (keys in CHART_MAP) are parsed; the scatter
    charts (intelligence-vs-cost etc.) carry no href/value text and are skipped.
    """
    with open(json_path) as f:
        data = json.load(f)
    out = {}
    for idx, key in CHART_MAP.items():
        if idx >= len(data):
            continue
        svg = data[idx].get("svg") or ""
        out[key] = _parse_chart(svg)
    return out


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    p = here / "aa_charts_export.json"
    res = parse_aa_charts(str(p))
    for k, v in res.items():
        print(f"{k}: {len(v)} rows; sample {v[:2]}")
