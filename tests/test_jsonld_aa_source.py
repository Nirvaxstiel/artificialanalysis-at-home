import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "sources" / "aa"
JSONLD = REPO / "data" / "sources" / "aa" / "aa_jsonld_export.json"


def _load_jsonld():
    with open(JSONLD) as f:
        return json.load(f)


def _load_registry():
    with open(REPO / "data" / "model_registry.json") as f:
        return json.load(f)


def _load_processed():
    raw = (REPO / "data" / "processed.js").read_text(encoding="utf-8")
    js = raw[raw.index("=") + 1:].rstrip().rstrip(";")
    data = json.loads(js)
    return data["models"]


def _gpt56_slugs():
    return [
        "gpt-5-6-luna-medium", "gpt-5-6-sol-medium", "gpt-5-6-terra-medium",
        "gpt-5-6-sol-high", "gpt-5-6-terra-high", "gpt-5-6-luna-high",
        "gpt-5-6-sol-xhigh", "gpt-5-6-luna-xhigh", "gpt-5-6-terra-xhigh",
        "gpt-5-6-sol", "gpt-5-6-luna", "gpt-5-6-terra",
    ]


# ── (A) JSON-LD contract: structure + dedup safety ──


class TestJsonLdContract:
    def test_file_is_dataset_list(self):
        d = _load_jsonld()
        assert isinstance(d, list)
        datasets = [ds for ds in d if ds.get("@type") == "Dataset"]
        assert datasets, "expected at least one schema.org Dataset"
        # A stray non-Dataset entry (e.g. FAQPage site boilerplate) is harmless.
        non_dataset = [ds.get("@type") for ds in d if ds.get("@type") != "Dataset"]
        assert all(t in (None, "FAQPage") for t in non_dataset), f"unexpected types: {non_dataset}"

    def test_expected_datasets_present(self):
        d = _load_jsonld()
        names = {ds.get("name") for ds in d}
        required = {
            "Intelligence", "Speed", "Cost per Task",
            "Artificial Analysis Coding Index",
            "AA-Omniscience Hallucination Rate",
            "AA-Briefcase Analytical Quality & Presentation Elo",
            "Time per Intelligence Index Task",
        }
        missing = required - names
        assert not missing, f"missing datasets: {missing}"

    def test_two_intelligence_datasets_are_value_identical(self):
        """Safe-dedup precondition: where slugs overlap, values must match."""
        d = _load_jsonld()
        by_name = {ds.get("name"): ds for ds in d}
        intel = {e["detailsUrl"].replace("/models/", ""): e
                 for e in by_name["Intelligence"]["data"]}
        ow = {e["detailsUrl"].replace("/models/", ""): e
              for e in by_name["Artificial Analysis Intelligence Index by Open Weights / Proprietary"]["data"]}
        shared = set(intel) & set(ow)
        assert shared, "expected overlapping slugs between the two intelligence datasets"
        for s in shared:
            a = intel[s].get("artificialAnalysisIntelligenceIndex")
            b = ow[s].get("intelligenceIndex")
            assert a is not None and b is not None, f"{s}: one dataset missing value"
            assert abs(a - b) < 1e-9, f"{s}: Intelligence ({a}) != OpenWeights ({b}) — NOT safe to dedup"

    def test_gpt56_variants_present_in_jsonld(self):
        d = _load_jsonld()
        labels = {e.get("label") for ds in d for e in ds.get("data", [])}
        assert any("GPT-5.6" in l for l in labels), "no GPT-5.6 labels found"


# ── (B) Ingestion: 12 new models land with data ──


class TestJsonLdIngestion:
    @pytest.fixture(scope="class")
    def registry(self):
        return _load_registry()

    @pytest.fixture(scope="class")
    def processed(self):
        return _load_processed()

    def test_12_gpt56_models_in_registry(self, registry):
        ids = {m["id"] for m in registry["models"]}
        missing = [s for s in _gpt56_slugs() if s not in ids]
        assert not missing, f"GPT-5.6 slugs missing from registry: {missing}"

    def test_12_gpt56_models_in_output(self, processed):
        ids = {m["slug"] for m in processed}
        missing = [s for s in _gpt56_slugs() if s not in ids]
        assert not missing, f"GPT-5.6 slugs missing from processed.js: {missing}"

    def test_intel_populated(self, processed):
        sol_max = next(m for m in processed if m["slug"] == "gpt-5-6-sol")
        assert sol_max.get("intel") is not None, "gpt-5-6-sol should have intel from JSON-LD"
        assert sol_max["intel"] > 50, f"unexpected intel value: {sol_max.get('intel')}"

    def test_speed_populated(self, processed):
        sol_max = next(m for m in processed if m["slug"] == "gpt-5-6-sol")
        assert sol_max.get("speed_tps") is not None, "gpt-5-6-sol should have speed_tps"

    def test_coding_index_populated(self, processed):
        sol_xhigh = next(m for m in processed if m["slug"] == "gpt-5-6-sol-xhigh")
        assert sol_xhigh.get("aa_coding_index") is not None, "gpt-5-6-sol-xhigh should have aa_coding_index"

    def test_time_per_task_axis_populated(self, processed):
        have = [m for m in processed if m.get("aa_time_per_task") is not None]
        gpt56 = [m for m in have if m["slug"].startswith("gpt-5-6")]
        assert len(gpt56) >= 5, f"expected >=5 GPT-5.6 with aa_time_per_task, got {len(gpt56)}"

    def test_omniscience_axis_wired_and_populated(self, processed):
        # Omniscience dataset has no GPT-5.6 entries, but the axis must exist and
        # be populated for at least one model (proves the axis + projection path works).
        have = [m for m in processed if m.get("aa_omniscience_hallucination_rate") is not None]
        assert len(have) >= 1, "aa_omniscience_hallucination_rate axis should be populated for >=1 model"

    def test_briefcase_axis_populated(self, processed):
        sol_max = next(m for m in processed if m["slug"] == "gpt-5-6-sol")
        assert sol_max.get("aa_briefcase_analytical_quality_elo") is not None, \
            "gpt-5-6-sol should have aa_briefcase_analytical_quality_elo"

    def test_cost_segments_populated(self, processed):
        luna_med = next(m for m in processed if m["slug"] == "gpt-5-6-luna-medium")
        # Output exposes flattened cost segments (cost_seg_reasoning etc.), not a
        # nested cost_segments dict.
        assert luna_med.get("cost_seg_reasoning") is not None, \
            "gpt-5-6-luna-medium should have cost_seg_reasoning from JSON-LD"
