"""Black-box contract tests for the Result monad (data/_result.py).

Test by input -> output only. No spying on internals, no mock invocations.
Each assertion checks the observable Result behaviour, not how it's built.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from _result import ok, err, from_fn  # noqa: E402


def test_ok_unwrap():
    assert ok(42).unwrap() == 42
    assert ok(42).is_ok() and not ok(42).is_err()


def test_err_unwrap_raises():
    e = err("boom")
    assert e.is_err() and not e.is_ok()
    with pytest.raises(ValueError):
        e.unwrap()


def test_err_unwrap_or_returns_default():
    assert err("x").unwrap_or(7) == 7


def test_bind_short_circuits_on_err():
    called = []
    r = err("stop").bind(lambda v: (called.append(v), ok(v * 2))[1])
    assert r.is_err()
    assert r.error == "stop"
    assert called == []  # step never ran


def test_bind_threads_ok():
    r = ok(3).bind(lambda v: ok(v + 1)).bind(lambda v: ok(v * 10))
    assert r.unwrap() == 40


def test_map_transforms_ok_only():
    assert ok(2).map(lambda v: v + 5).unwrap() == 7
    assert err("e").map(lambda v: v + 5).is_err()


def test_unwrap_or_default_chain():
    assert err("e").unwrap_or(0) == 0
    assert ok(9).unwrap_or(0) == 9


def test_from_fn_captures_exception():
    r = from_fn(lambda: 1 / 0)
    assert r.is_err()
    assert isinstance(r.error, ZeroDivisionError)


def test_from_fn_wraps_value():
    assert from_fn(lambda: "v").unwrap() == "v"


def test_match_dispatches():
    assert ok(5).match(ok=lambda v: f"ok:{v}", err=lambda e: f"err:{e}") == "ok:5"
    assert err("z").match(ok=lambda v: f"ok:{v}", err=lambda e: f"err:{e}") == "err:z"
