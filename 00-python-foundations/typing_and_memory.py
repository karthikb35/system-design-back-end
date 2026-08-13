"""
00 — Python Mastery: Typing, Custom Context Managers & Memory Model
===================================================================

Runnable companion to PDF Book I "Advanced Python — types, resources, memory".

Three senior-level topics:

  * TYPING     — type hints don't change runtime behavior but power tooling
                 (mypy/Pylance), self-document, and enable generics/Protocols
                 (structural "duck" typing you can check).
  * CONTEXT    — the @contextmanager decorator is the concise way to write a
    MANAGERS     with-block resource guard (setup / yield / teardown), and
                 contextlib.suppress ignores chosen exceptions.
  * MEMORY     — CPython frees objects by REFERENCE COUNTING (immediate) plus a
                 cyclic GC for reference cycles. weakref lets you reference an
                 object WITHOUT keeping it alive (great for caches).
"""

import gc
import sys
import weakref
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar


# --------------------------------------------------------------------------
# TYPING: a generic stack + a Protocol (structural typing). These are checked
# by static tools; at runtime we just assert the behavior is correct.
# --------------------------------------------------------------------------
T = TypeVar("T")


class Stack(Generic[T]):
    """A type-safe stack: Stack[int] vs Stack[str] are distinct to a type checker."""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def __len__(self) -> int:
        return len(self._items)


class SupportsArea(Protocol):
    """Structural typing: ANY object with .area() -> float satisfies this,
    no inheritance required (duck typing you can statically verify)."""

    def area(self) -> float: ...


@dataclass
class Circle:
    r: float

    def area(self) -> float:
        return 3.14159 * self.r * self.r


@dataclass
class Square:
    side: float

    def area(self) -> float:
        return self.side * self.side


def total_area(shapes: list[SupportsArea]) -> float:
    return sum(s.area() for s in shapes)


def typing_demo() -> None:
    s: Stack[int] = Stack()
    s.push(1)
    s.push(2)
    assert len(s) == 2
    assert s.pop() == 2
    # Circle and Square share NO base class, yet both satisfy SupportsArea.
    shapes = [Circle(2), Square(3)]
    assert abs(total_area(shapes) - (3.14159 * 4 + 9)) < 1e-6
    print("   typing: generic Stack[T] + Protocol (structural) — checked statically, correct at runtime")


# --------------------------------------------------------------------------
# CUSTOM CONTEXT MANAGER via @contextmanager: setup -> yield -> teardown, with
# teardown guaranteed even on exceptions. Cleaner than a class for simple cases.
# --------------------------------------------------------------------------
@contextmanager
def timing(log: list):
    log.append("enter")
    try:
        yield log                       # value bound to `as`
    finally:
        log.append("exit")              # always runs (like __exit__)


def context_manager_demo() -> None:
    log: list = []
    with timing(log) as l:
        l.append("body")
    assert log == ["enter", "body", "exit"]

    log2: list = []
    with suppress(ZeroDivisionError):   # swallow a specific exception, tidily
        with timing(log2):
            _ = 1 / 0                    # raises, but teardown still runs
    assert log2 == ["enter", "exit"]     # 'exit' proves finally ran on error
    print("   context manager: @contextmanager (setup/yield/teardown) + suppress() for chosen errors")


# --------------------------------------------------------------------------
# MEMORY: reference counting frees objects immediately when the last reference
# goes away; the cyclic GC cleans up reference CYCLES that refcounting can't.
# --------------------------------------------------------------------------
def refcount_demo() -> None:
    a = ["x", "y", "z"]
    base = sys.getrefcount(a)            # +1 temporary ref from the call itself
    b = a                               # new reference to the same list
    assert sys.getrefcount(a) == base + 1
    del b                               # drop it again
    assert sys.getrefcount(a) == base
    print("   refcount: each new binding raises the count; dropping it lowers it (immediate free at 0)")


def cyclic_gc_demo() -> None:
    class Node:
        def __init__(self):
            self.ref = None

    # Build a cycle: refcounting alone can NEVER free this (each keeps the other alive).
    x, y = Node(), Node()
    x.ref = y
    y.ref = x
    wx = weakref.ref(x)                  # observe without keeping alive
    del x, y                            # refcounts still > 0 due to the cycle
    collected = gc.collect()            # the cyclic collector breaks it
    assert wx() is None, "cyclic GC should have reclaimed the cycle"
    assert collected >= 0
    print("   cyclic GC: reference cycles are reclaimed by gc.collect(), not by refcounting")


def weakref_demo() -> None:
    class Big:
        pass

    obj = Big()
    cache = weakref.WeakValueDictionary()
    cache["k"] = obj                    # cache does NOT keep obj alive on its own
    assert cache.get("k") is obj
    del obj                             # last strong ref gone
    assert cache.get("k") is None       # entry vanished automatically — no leak
    print("   weakref: a WeakValueDictionary cache never keeps its values alive (leak-free cache)")


def main() -> None:
    print("=" * 70)
    print("PYTHON MASTERY — typing_and_memory.py")
    print("=" * 70)
    print("1. Typing (generics + Protocol/structural typing):")
    typing_demo()
    print("2. Custom context managers (@contextmanager + suppress):")
    context_manager_demo()
    print("3. Reference counting:")
    refcount_demo()
    print("4. Cyclic garbage collection:")
    cyclic_gc_demo()
    print("5. weakref (leak-free caches):")
    weakref_demo()
    print("-" * 70)
    print("All typing_and_memory demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8")
    main()
