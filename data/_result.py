"""Result monad (Either) for result-oriented, error-short-circuiting pipelines.

A Result is either Ok(value) or Err(error). `.bind` (>>=) threads a value through
a step that returns another Result; on Err the chain short-circuits. `.pipe` composes
a left-to-right flow: pipe(x, f, g, h) == f(x).bind(g).bind(h). `do` collects a list
of steps, stops at the first Err, and returns Ok([...]) with every Ok value.

No dependencies, no I/O. Importable from tests and pipeline stages alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def bind(self, f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return f(self.value)

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        return Ok(f(self.value))

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, _default: U) -> T:
        return self.value

    def match(self, *, ok: Callable[[T], Any], err: Callable[[E], Any]) -> Any:
        return ok(self.value)


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def bind(self, _f: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return Err(self.error)

    def map(self, _f: Callable[[T], U]) -> "Result[U, E]":
        return Err(self.error)

    def unwrap(self) -> T:
        raise ValueError(f"unwrap on Err: {self.error}")

    def unwrap_or(self, default: U) -> U:
        return default

    def match(self, *, ok: Callable[[T], Any], err: Callable[[E], Any]) -> Any:
        return err(self.error)


Result = "Ok[T, E] | Err[E]"


def ok(value: T) -> Ok[T]:
    return Ok(value)


def err(error: E) -> Err[E]:
    return Err(error)


def pipe(value: T, *steps: Callable[[Any], "Result[Any, E]"]) -> "Result[Any, E]":
    """Left-to-right Result flow. pipe(x, f, g) == f(x).bind(g)."""
    result: Result[Any, E] = ok(value)
    for step in steps:
        if result.is_err():
            return result
        result = result.bind(step)
    return result


def do(*steps: Callable[[], "Result[T, E]"]) -> "Result[list[T], E]":
    """Run steps in order; stop at first Err; Ok collects every Ok value."""
    values: list[T] = []
    for step in steps:
        r = step()
        if r.is_err():
            return r
        values.append(r.unwrap())
    return ok(values)


def from_fn(fn: Callable[[], T]) -> "Result[T, Exception]":
    """Wrap a side-effecting call; failures become Err(Exception)."""
    try:
        return ok(fn())
    except Exception as e:  # noqa: BLE001 — intended boundary capture
        return err(e)
