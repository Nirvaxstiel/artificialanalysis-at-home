"""Black-box contract tests for the Result monad (data/_result.py).

Test by input -> output only. No spying on internals, no mock invocations.
Each assertion checks the observable Result behaviour, not how it's built.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from _result import ok, err, pipe, do, from_fn  # noqa: E402


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


def test_pipe_left_to_right():
    inc = lambda v: ok(v + 1)
    dbl = lambda v: ok(v * 2)
    r = pipe(1, inc, dbl, inc)
    assert r.unwrap() == 5  # ((1+1)*2)+1


def test_pipe_stops_at_first_err():
    calls = []
    r = pipe(1,
             lambda v: (calls.append(v), ok(v))[1],
             lambda _: err("fail"),
             lambda v: (calls.append("late"), ok(v))[1])
    assert r.is_err()
    assert r.error == "fail"
    assert calls == [1]  # third step never ran


def test_do_collects_when_all_ok():
    r = do(lambda: ok(1), lambda: ok(2), lambda: ok(3))
    assert r.unwrap() == [1, 2, 3]


def test_do_stops_at_first_err():
    r = do(lambda: ok(1), lambda: err("nope"), lambda: ok(3))
    assert r.is_err()
    assert r.error == "nope"


def test_from_fn_captures_exception():
    r = from_fn(lambda: 1 / 0)
    assert r.is_err()
    assert isinstance(r.error, ZeroDivisionError)


def test_from_fn_wraps_value():
    assert from_fn(lambda: "v").unwrap() == "v"


def test_match_dispatches():
    assert ok(5).match(ok=lambda v: f"ok:{v}", err=lambda e: f"err:{e}") == "ok:5"
    assert err("z").match(ok=lambda v: f"ok:{v}", err=lambda e: f"err:{e}") == "err:z"
