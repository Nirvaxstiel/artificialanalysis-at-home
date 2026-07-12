"""Black-box Result-contract tests for data/_canonical.py resolvers.

Asserts the observable Ok/Err behaviour of the miss-returning canonical
resolvers after the monadic refactor. No data files, no internal spying — call
the public functions and check Result shape + unwrap_or round-trip.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from _canonical import (  # noqa: E402
    openllm_name_to_canonical,
    costbd_name_to_canonical,
    dirac_name_to_canonical,
    canonical_to_or_id,
)
from _result import ok  # noqa: E402


def test_openllm_empty_name_err():
    assert openllm_name_to_canonical("").is_err()


def test_openllm_resolves_ok():
    # openllm names route through resolve_from_slug (passthrough-capable)
    r = openllm_name_to_canonical("mistralai/Mixtral-8x7B-Instruct-v0.1")
    assert r.is_ok()


def test_costbd_hit_ok_miss_err():
    hit = costbd_name_to_canonical("DeepSeek V4 Pro (max)")
    assert hit.is_ok()
    assert hit.unwrap() == "deepseek-v4-pro"
    assert costbd_name_to_canonical("No Such Model XYZ").is_err()


def test_dirac_hit_ok_miss_err():
    hit = dirac_name_to_canonical("DeepSeek_DeepSeek_V4_Pro")
    assert hit.is_ok()
    assert hit.unwrap() == "deepseek-v4-pro"
    assert dirac_name_to_canonical("Novel_Model_99").is_err()


def test_canonical_to_or_id_hit_ok_miss_err():
    hit = canonical_to_or_id("gemini-3-pro")
    assert hit.is_ok()
    assert hit.unwrap() == "google/gemini-3-pro"
    assert canonical_to_or_id("some-unmapped-slug").is_err()


def test_unwrap_or_round_trips_old_behavior():
    # .unwrap_or(None) reproduces the prior None-returning contract for callers
    assert openllm_name_to_canonical("").unwrap_or(None) is None
    assert dirac_name_to_canonical("Novel_Model_99").unwrap_or(None) is None
    assert isinstance(costbd_name_to_canonical("DeepSeek V4 Pro (max)").unwrap_or(None), str)
