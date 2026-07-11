"""Black-box tests for the monadic Pipeline orchestration (data/_pipeline.py).

No real I/O: steps are in-memory lambdas returning Result values. We assert the
OBSERVABLE orchestration contract: steps run in order, a failing step (Err or
raised exception) short-circuits, and Ok values accumulate into ctx.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from _pipeline import Pipeline  # noqa: E402
from _result import ok, err  # noqa: E402


def test_steps_run_in_order_and_accumulate():
    order = []
    p = (Pipeline()
         .then("a", lambda ctx: (order.append("a"), ok(1))[1])
         .then("b", lambda ctx: (order.append("b"), ok(2))[1])
         .then("c", lambda ctx: (order.append("c"), ok(3))[1])
         .run())
    assert order == ["a", "b", "c"]
    assert p["a"] == 1 and p["b"] == 2 and p["c"] == 3
    assert "_error" not in p


def test_err_step_short_circuits():
    order = []
    p = (Pipeline()
         .then("a", lambda ctx: (order.append("a"), ok(1))[1])
         .then("b", lambda ctx: (order.append("b"), err("boom"))[1])
         .then("c", lambda ctx: (order.append("c"), ok(3))[1])
         .run())
    assert order == ["a", "b"]          # c never ran
    assert p["_failed_step"] == "b"
    assert p["_error"] == "boom"
    assert "c" not in p


def test_raised_exception_is_captured_as_err():
    order = []
    def boom(ctx):
        order.append("x")
        raise RuntimeError("kaboom")
    p = (Pipeline()
         .then("x", boom)
         .then("y", lambda ctx: (order.append("y"), ok(9))[1])
         .run())
    assert order == ["x"]               # y never ran
    assert p["_failed_step"] == "x"
    assert isinstance(p["_error"], RuntimeError)


def test_empty_pipeline_completes():
    p = Pipeline().run()
    assert isinstance(p, dict)
    assert "_error" not in p
