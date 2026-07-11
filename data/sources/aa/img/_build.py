import json, os
from pathlib import Path

from ...._canonical import aa_img_name_to_canonical, resolve_from_slug


def get_aa_img_scraped_cids(base: Path) -> set[str]:
    """Canonical ids the AA image scraper actually fetched (aa_scrape_progress.json).

    Repurposes the orphan scrape-tracker as a provenance signal: an AA_IMG
    (speculative) model is 'confirmed' if it was scraped from a real chart, vs
    a pure projection. Distinct from the model's speculative flag. The tracker
    stores AA slugs, so we resolve them to canonical ids for join.
    """
    path = os.path.join(base, "data", "sources", "aa", "aa_scrape_progress.json")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        data = json.load(f)
    cids = set()
    for slug in data.get("scraped", []):
        cid = resolve_from_slug(slug)
        if cid:
            cids.add(cid)
    return cids


def get_aa_img_models(base: Path) -> dict[str, dict]:
    img_path = os.path.join(base, "data", "sources", "aa", "img", "aa_img_models.json")
    if not os.path.exists(img_path):
        return {}

    with open(img_path) as f:
        raw = json.load(f)

    scraped = get_aa_img_scraped_cids(base)

    out: dict[str, dict] = {}
    for display_name, rec in raw.items():
        if display_name == "_meta":
            continue
        cid = aa_img_name_to_canonical(display_name).unwrap_or(None)
        if not cid:
            continue
        b = out.setdefault(cid, {}).setdefault("benchmarks", {}).setdefault("aa_img", {})
        for k in (
            "omniscience_index", "omniscience_accuracy",
            "omniscience_hallucination_rate", "briefcase_elo",
            "briefcase_analytical_quality_elo", "briefcase_presentation_elo",
            "briefcase_rubric_score", "agentic_index", "coding_index",
            "openness_index", "e2e_response_time_s", "ttft_variance",
        ):
            if rec.get(k) is not None:
                b.setdefault(k, rec[k])
        if rec.get("cost_per_task") is not None:
            out[cid].setdefault("pricing", {}).setdefault("aa", {})["cost_per_task"] = rec["cost_per_task"]
        meta = out[cid].setdefault("meta", {})
        if rec.get("params_total_b") is not None:
            meta.setdefault("params_total_b", rec["params_total_b"])
        if rec.get("params_active_b") is not None:
            meta.setdefault("params_active_b", rec["params_active_b"])
        if cid in scraped:
            meta.setdefault("confirmed_scraped", True)

    return out
