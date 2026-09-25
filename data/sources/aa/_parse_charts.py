import json
import os
import re
from pathlib import Path

from _result import ok, err


def _load_json(path: str):
    try:
        return ok(json.loads(Path(path).read_text(encoding="utf-8-sig")))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        return err(f"{os.path.basename(path)}: {e}")


CHART_TITLE_MAP: dict[str, str] = {
    "artificial analysis intelligence index by open weights / proprietary": "intel",
    "pricing: cache hit, input, and output": "pricing",
    "cost per intelligence index task": "cost_per_task",
    "output speed": "output_speed",
    "time per intelligence index task": "time_per_task",
    "artificial analysis finance & accounting index": "finance_accounting_index",
    "aa-analystagent pass^5": "analyst_agent_pass_5",
    "aa-briefcase elo": "briefcase_elo",
    "gdpval-aa v2.1 leaderboard": "gdpval_elo",
    "aa-omniscience index": "omniscience_index",
}


def _chart_key(spans):
    title = spans[0].strip().lower() if isinstance(spans, list) and spans else ""
    return CHART_TITLE_MAP.get(title)


def _norm_value(text: str):
    t = text.strip().replace("−", "-")
    t = t.replace("&lt;", "<").replace("&gt;", ">")
    is_pct = "%" in t
    is_less_than = t.startswith("<")
    t = t.replace("$", "").replace("%", "").replace(",", "")
    m = re.fullmatch(r"<?\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", t)
    if not m:
        return None
    val = float(m.group(1))
    if is_less_than:
        val = -abs(val)
    if is_pct:
        val = val / 100.0
    return val


def _extract_slugs(svg: str):
    """All model slugs in render order (from <a href='/models/{slug}'>)."""
    return re.findall(r'href="/models/([a-z0-9\-]+)"', svg)


def _extract_values(svg: str):
    """All numeric-ish label values in render order (from <text> nodes)."""
    texts = re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)
    extracted_values = []
    for t in texts:
        inner = re.sub(r"<[^>]+>", "", t).strip()
        if not inner:
            continue
        if re.search(r"[\d]", inner) and not re.search(r"[A-Za-z]", inner.replace("%", "").replace("$", "").replace("<", "").replace(",", "").replace(".", "")):
            v = _norm_value(inner)
            if v is not None:
                extracted_values.append(v)
    return extracted_values


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
    return []


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
    x_values = []
    for x, v in re.findall(r'<text[^>]*x="([\d.]+)"[^>]*>\s*\$?<?\s*([\d.]+)\s*</text>', group_svg):
        x_values.append((float(x), float(v)))
    return x_values


def _align_x_to_models(xvals: list, ref_xs: list):
    """Map each (x, value) to a model index by x-band, using ref_xs as the
    per-model column axis (sorted x of a complete series). Returns {idx: value}."""
    if not ref_xs:
        return {}
    ref = sorted(ref_xs)
    span = (ref[-1] - ref[0]) / max(1, len(ref) - 1)
    aligned = {}
    for x, v in xvals:
        idx = round((x - ref[0]) / span) if span > 0 else 0
        aligned[idx] = v
    return aligned


def _parse_pricing(svg: str):
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
    parsed_rows = []
    for idx in sorted(per_model):
        if idx >= len(hrefs):
            continue
        parsed_rows.append((hrefs[idx], per_model[idx]))
    return parsed_rows


def _parse_cost_per_task(svg: str):
    hrefs = _extract_slugs(svg)
    if not hrefs:
        return []
    groups = [_extract_x_values(group) for group in _extract_label_lists(svg)]
    reference = max(groups, key=len, default=[])
    if len(reference) != len(hrefs):
        return []
    aligned = _align_x_to_models(reference, [x for x, _ in reference])
    if set(aligned) != set(range(len(hrefs))):
        return []
    return [(hrefs[index], aligned[index]) for index in range(len(hrefs))]


def parse_aa_charts(json_path: str) -> "Ok[dict]|Err[str]":
    loaded = _load_json(json_path)
    if loaded.is_err():
        return err(loaded.error)
    data = loaded.unwrap()
    if not isinstance(data, list) or any(not isinstance(entry, dict) for entry in data):
        return err("AA chart export must be a list of objects")
    chart_data = {}
    for entry in data:
        key = _chart_key(entry.get("spans", []))
        if key is None:
            continue
        svg = entry.get("svg") or ""
        if "recharts-surface" not in svg:
            continue
        if key == "pricing":
            rows = _parse_pricing(svg)
        elif key == "cost_per_task":
            rows = _parse_cost_per_task(svg)
        else:
            rows = _parse_chart(svg)
        if not rows:
            continue
        chart_data[key] = rows
    return ok(chart_data)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    p = here / "aa_charts_export.json"
    res = parse_aa_charts(str(p))
    if res.is_err():
        print("PARSE FAILED:", res.error)
        raise SystemExit(1)
    for k, v in res.unwrap().items():
        print(f"{k}: {len(v)} rows; sample {v[:2]}")
