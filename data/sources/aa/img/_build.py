import json, os
from pathlib import Path

from ...._canonical import aa_img_name_to_canonical


def get_aa_img_models(base: Path) -> dict[str, dict]:
    img_path = os.path.join(base, "data", "sources", "aa", "img", "aa_img_models.json")
    if not os.path.exists(img_path):
        return {}

    with open(img_path) as f:
        raw = json.load(f)

    out: dict[str, dict] = {}
    for display_name, rec in raw.items():
        if display_name == "_meta":
            continue
        cid = aa_img_name_to_canonical(display_name)
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

    return out
