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


def _extract_label_lists(svg: str):
    """Return list of label-list group SVGs (each recharts-label-list block)."""
    bounds = [m.end() for m in re.finditer(r'recharts-label-list', svg)]
    groups = []
    for i, start in enumerate(bounds):
        end = bounds[i + 1] if i + 1 < len(bounds) else len(svg)
        groups.append(svg[start:end])
    return groups


def _extract_x_values(group_svg: str):
    """All ($)numeric <text> values in a group, with their x-coordinate."""
    out = []
    for x, v in re.findall(r'<text[^>]*x="([\d.]+)"[^>]*>\s*\$?<?\s*([\d.]+)\s*</text>', group_svg):
        out.append((float(x), float(v)))
    return out


def _align_x_to_models(xvals: list, ref_xs: list):
    """Map each (x, value) to a model index by x-band, using ref_xs as the
    per-model column axis (sorted x of a complete series). Returns {idx: value}."""
    if not ref_xs:
        return {}
    ref = sorted(ref_xs)
    span = (ref[-1] - ref[0]) / max(1, len(ref) - 1)
    out = {}
    for x, v in xvals:
        idx = round((x - ref[0]) / span) if span > 0 else 0
        out[idx] = v
    return out


def _parse_pricing(svg: str):
    """Parse the Pricing chart (#9) → [(slug, {cache_hit, inp, out}), ...].

    The chart title names 3 series ("Cache Hit, Input, and Output") matching the
    3 recharts-label-list groups. Each value <text> carries an x-coordinate; we
    align values to model columns by x-band (rounding to the per-model spacing
    derived from the complete Input series). Cache-hit is sparse (some models
    lack it) so it's optional per model. Validated against the AA live API.
    """
    hrefs = _extract_slugs(svg)
    groups = _extract_label_lists(svg)
    if len(groups) < 3 or not hrefs:
        return []
    series = ["cache_hit", "inp", "out"]
    parsed = [_extract_x_values(g) for g in groups[:3]]
    # Reference axis = the complete series (most values) for stable spacing.
    ref = max(parsed, key=len)
    ref_xs = [x for x, _ in ref]
    per_model = {}
    for name, xvals in zip(series, parsed):
        for idx, val in _align_x_to_models(xvals, ref_xs).items():
            per_model.setdefault(idx, {})[name] = val
    out = []
    for idx in sorted(per_model):
        if idx >= len(hrefs):
            continue
        out.append((hrefs[idx], per_model[idx]))
    return out


def parse_aa_charts(json_path: str) -> dict[str, list]:
    """Parse the method-2 SVG scrape → {chart_key: [(slug, value), ...]}.

    Only the 7 ranking/bar charts (keys in CHART_MAP) are parsed; the scatter
    charts (intelligence-vs-cost etc.) carry no href/value text and are skipped.
    The Pricing chart (#9) uses a dedicated x-aligned parser.
    """
    with open(json_path) as f:
        data = json.load(f)
    out = {}
    for idx, key in CHART_MAP.items():
        if idx >= len(data):
            continue
        svg = data[idx].get("svg") or ""
        if key == "pricing":
            out[key] = _parse_pricing(svg)
        else:
            out[key] = _parse_chart(svg)
    return out


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    p = here / "aa_charts_export.json"
    res = parse_aa_charts(str(p))
    for k, v in res.items():
        print(f"{k}: {len(v)} rows; sample {v[:2]}")
