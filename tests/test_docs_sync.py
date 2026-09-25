"""Guard: counts and dates stated in the docs must match the generated artifacts.

Every number in README.md / the vault note / viz/README.md / DATA-ACQUISITION.md
is hand-written prose. This test fails the build when prose drifts from
data/processed.js + data/model_registry.json (the single generated source),
so "123 rendered vs 120 in the layout" style contradictions cannot ship.
"""
import json, re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

STALE_STRINGS = [
    "2279",
    "AA Intelligence Index v4.1",
    "31 July 2026",
    "(117 models total)",
    "117 models",
]


@pytest.fixture(scope="module")
def processed_meta():
    raw = (DATA / "processed.js").read_text(encoding="utf-8").strip()
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    return json.loads(raw)["meta"]


@pytest.fixture(scope="module")
def registry_meta():
    return json.loads((DATA / "model_registry.json").read_text(encoding="utf-8"))["meta"]


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def test_docs_creator_counts_match_processed_meta(processed_meta):
    expected = processed_meta["counts"]["creators"]
    for doc in ("README.md", "LLM Provider Pricing Analysis.md"):
        found = [int(n) for n in re.findall(r"(\d+) creators", _read(doc))]
        assert found, f"{doc}: must state the generated creator count ({expected})"
        assert set(found) == {expected}, f"{doc}: creator counts {found} != generated {expected}"


def test_docs_carry_the_generated_counts(processed_meta):
    counts = processed_meta["counts"]
    for doc in ("README.md", "LLM Provider Pricing Analysis.md", "viz/README.md"):
        text = _read(doc)
        assert str(counts["models"]) in text, f"{doc}: must state the dataset size {counts['models']}"
        assert str(counts["aa_models"]) in text, f"{doc}: must state the AA-covered count {counts['aa_models']}"


def test_docs_have_no_stale_counts(processed_meta):
    for doc in ("README.md", "LLM Provider Pricing Analysis.md", "viz/README.md", "DATA-ACQUISITION.md"):
        text = _read(doc)
        stale = [s for s in STALE_STRINGS if s in text]
        assert not stale, f"{doc}: stale strings {stale} — regenerate the docs from processed.js meta"


def test_readme_source_counts_match_sources_meta(processed_meta):
    sources = processed_meta["sources_meta"]
    text = _read("README.md")
    for pattern, expected in [
        (r"Coding/agentic/reasoning scores \((\d+) models\)", sources["LiveBench"]["models"]),
        (r"Parameter counts \((\d+) models in subset\)", sources["OpenLLM v2"]["models"]),
        (r"context window for ~(\d+) models", sources["OpenRouter"]["models"]),
        (r"Code \+ Text Elo \((\d+) / (\d+) models\)", None),
    ]:
        m = re.search(pattern, text)
        assert m, f"README source-count sentence changed shape: {pattern}"
        if expected is None:
            assert [int(g) for g in m.groups()] == [
                sources["Arena Text"]["models"], sources["Arena Code"]["models"]]
        else:
            assert int(m.group(1)) == expected, f"{pattern} != generated {expected}"


def test_processed_meta_is_derived_from_registry(processed_meta, registry_meta):
    assert processed_meta["sources_meta"] == registry_meta["source_meta"]
    assert processed_meta["sources"] == registry_meta["sources"]
    for name, info in processed_meta["sources_meta"].items():
        assert isinstance(info["models"], int), f"{name}: models count must be generated"
        assert info["as_of"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", info["as_of"]), \
            f"{name}: as_of must be an ISO date or null, got {info['as_of']!r}"


def test_documented_snapshot_rows_match_source_files(processed_meta):
    aa_live = json.loads((DATA / "sources" / "aa" / "aa_api_live.json").read_text(encoding="utf-8"))
    aa_catalog = json.loads((DATA / "sources" / "aa" / "aa_public_model_catalog.json").read_text(encoding="utf-8"))
    dirac = json.loads((DATA / "sources" / "dirac" / "cache_hit_rates.json").read_text(encoding="utf-8"))
    misc = json.loads((DATA / "sources" / "misc.json").read_text(encoding="utf-8"))
    acquisition = _read("DATA-ACQUISITION.md")
    for label, count in (("aa_api_live", len(aa_live["data"])), ("aa_public_catalog", len(aa_catalog["models"])), ("dirac", len(dirac)), ("misc", len(misc))):
        assert f"({count} " in acquisition or f"({count} models)" in acquisition, \
            f"DATA-ACQUISITION.md: {label} row must state its real row count ({count})"
    assert str(len(aa_live["data"])) in acquisition
