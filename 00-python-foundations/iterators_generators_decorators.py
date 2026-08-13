"""
00 — Python Foundations: Iterators, Generators, Decorators
==========================================================

Runnable companion to PDF Chapter "P+ — Python Foundations"
(iterators/generators/decorators sections).

  * Iterator protocol (__iter__/__next__)
  * Generators (yield) and lazy pipelines
  * Generator expressions
  * Decorators (timing, memoization, retry) with functools.wraps

Run:  python iterators_generators_decorators.py
"""

from __future__ import annotations

import functools
import time
from collections.abc import Iterator


# ===========================================================================
# ITERATOR PROTOCOL — the machinery behind every `for` loop
# ===========================================================================
class Countdown:
    """A hand-written iterator: implements __iter__ and __next__."""

    def __init__(self, start: int) -> None:
        self.current = start

    def __iter__(self) -> "Countdown":
        return self

    def __next__(self) -> int:
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1


# ===========================================================================
# GENERATORS — the easy way to make an iterator (lazy, memory-cheap)
# ===========================================================================
def countdown(n: int) -> Iterator[int]:
    while n > 0:
        yield n  # produces one value at a time; state is suspended between calls
        n -= 1


def fibonacci() -> Iterator[int]:
    """An INFINITE generator — impossible with a list."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def take(gen: Iterator[int], k: int) -> list[int]:
    return [next(gen) for _ in range(k)]


# ===========================================================================
# DECORATORS — add behavior without editing the wrapped function
# ===========================================================================
def timed(fn):
    @functools.wraps(fn)  # preserve name/docstring of the wrapped function
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        wrapper.last_seconds = time.perf_counter() - start  # type: ignore[attr-defined]
        return result

    wrapper.last_seconds = 0.0  # type: ignore[attr-defined]
    return wrapper


def retry(times: int = 3):
    """A decorator FACTORY — parameterized decorator."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 (demo)
                    last_exc = exc
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


def memoize(fn):
    cache: dict[tuple, object] = {}

    @functools.wraps(fn)
    def wrapper(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]

    wrapper.cache = cache  # type: ignore[attr-defined]
    return wrapper


@memoize
def slow_square(n: int) -> int:
    return n * n


@timed
def sum_to(n: int) -> int:
    return sum(range(n))


_flaky_calls = {"n": 0}


@retry(times=3)
def flaky() -> str:
    _flaky_calls["n"] += 1
    if _flaky_calls["n"] < 3:
        raise ConnectionError("transient")
    return "ok"


def main() -> None:
    print("=" * 68)
    print("PYTHON FOUNDATIONS — iterators_generators_decorators.py")
    print("=" * 68)

    assert list(Countdown(3)) == [3, 2, 1]
    assert list(countdown(3)) == [3, 2, 1]
    print("iterators/generators: countdown ->", list(countdown(3)))

    # Infinite generator, consumed lazily.
    assert take(fibonacci(), 8) == [0, 1, 1, 2, 3, 5, 8, 13]
    print("infinite generator: first 8 fibs ->", take(fibonacci(), 8))

    # Generator expression — lazy, no giant list materialized.
    total = sum(n * n for n in range(1_000))
    assert total == 332_833_500
    print("generator expression: sum of squares < 1000 ->", total)

    # Decorators
    assert sum_to(1_000) == 499_500
    print(f"@timed: sum_to(1000) ran in {sum_to.last_seconds:.6f}s")

    assert slow_square(12) == 144 and slow_square(12) == 144
    assert (12,) in slow_square.cache
    print("@memoize: 12^2 cached ->", slow_square.cache)

    assert flaky() == "ok" and _flaky_calls["n"] == 3
    print("@retry: succeeded on attempt", _flaky_calls["n"])

    print("-" * 68)
    print("All iterator/generator/decorator demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
