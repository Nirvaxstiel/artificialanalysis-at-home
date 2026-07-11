"""Orchestrated monadic build pipeline — pull -> registry -> axes -> dashboard.

Each stage returns a Result (Ok(ctx_update) | Err(reason)); the pipeline threads
the shared ctx and short-circuits at the first Err instead of raising. Steps that
throw are captured into Err so a failed stage is a value, not an exception.

Usage:
    python -m data._pipeline          # full rebuild (pull sources + build)
    python -m data._pipeline build    # skip pull, rebuild from cached sources
"""

import time, sys, os
from pathlib import Path

from _result import ok

ROOT = Path(__file__).resolve().parent.parent  # repo root


def _is_result(x) -> bool:
    """Duck-type a Result (Ok/Err both expose is_ok/is_err)."""
    return hasattr(x, "is_ok") and hasattr(x, "is_err")


class Pipeline:
    """Monadic pipeline — compose build steps that return Result, with timing."""

    def __init__(self, ctx: dict | None = None):
        self.ctx = ctx or {"root": ROOT}
        self._steps: list[tuple[str, callable]] = []

    def then(self, name: str, fn: callable) -> "Pipeline":
        self._steps.append((name, fn))
        return self

    def run(self) -> dict:
        for name, fn in self._steps:
            t0 = time.time()
            print(f"\n─── {name} ───")
            try:
                returned = fn(self.ctx)
            except Exception as e:  # noqa: BLE001 — capture stage failure as Err
                print(f"  ✗ {name} FAILED: {e}")
                self.ctx["_failed_step"] = name
                self.ctx["_error"] = e
                return self.ctx
            result = returned if _is_result(returned) else ok(returned)
            if result.is_err():
                print(f"  ✗ {name} FAILED: {result.error}")
                self.ctx["_failed_step"] = name
                self.ctx["_error"] = result.error
                return self.ctx
            self.ctx[name] = result.unwrap()
            print(f"  ✓ {name} ({time.time()-t0:.1f}s)")
        print(f"\n{'='*50}\nPipeline complete ({time.time()-self.ctx.get('_start', time.time()):.1f}s)")
        return self.ctx


def _resolve_module(name: str):
    """Import a data pipeline module by name."""
    import importlib
    return importlib.import_module(f"data.{name}")


def step(name: str) -> callable:
    """Wrap a module's run() (which returns a Result) as a pipeline step."""
    mod = _resolve_module(name)
    def _step(ctx):
        return mod.run(ctx)
    _step.__name__ = name
    _step.__qualname__ = name
    return _step


def build():
    """Full rebuild: pull sources, then build from cache."""
    (Pipeline()
        .then("pull_sources", step("_pull_sources"))
        .then("build_registry", step("_build_registry"))
        .then("build_axes", step("_build_axes"))
        .then("build_dashboard", lambda ctx: _resolve_module("_build_dashboard_data").build(ctx))
        .run())


def build_from_cache():
    """Rebuild from cached sources (skip pull)."""
    (Pipeline()
        .then("build_registry", step("_build_registry"))
        .then("build_axes", step("_build_axes"))
        .then("build_dashboard", lambda ctx: _resolve_module("_build_dashboard_data").build(ctx))
        .run())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_from_cache()
    else:
        build()
