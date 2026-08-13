"""
00 — Python Foundations: Types, Control Flow, Collections, Functions
====================================================================

Runnable companion to PDF Chapter "P+ — Python Foundations".

Covers, with executable demos:
  * variables, immutable vs mutable types, `==` vs `is`
  * operators and truthiness
  * control flow (if/elif/else, for/while, for-else, match)
  * the four built-in collections (list, tuple, set, dict) + `collections` upgrades
  * functions, defaults, *args/**kwargs, lambdas, comprehensions, functional tools
  * file handling with context managers
  * exception handling (EAFP)

Run:  python fundamentals.py
"""

from __future__ import annotations

import json
import tempfile
from collections import Counter, defaultdict, deque
from functools import reduce
from pathlib import Path


# ===========================================================================
# 1. VARIABLES, TYPES, `==` vs `is`
# ===========================================================================
def demo_types_and_identity() -> None:
    x = 42            # int (immutable)
    pi = 3.14         # float
    name = "Ada"      # str (immutable)
    ok = True         # bool
    nothing = None    # the "no value" singleton

    a, b = 1, 2
    a, b = b, a       # tuple unpacking -> swap with no temp
    assert (a, b) == (2, 1)

    # `==` compares VALUES; `is` compares IDENTITY (same object).
    list1 = [1, 2, 3]
    list2 = [1, 2, 3]
    assert list1 == list2       # equal values
    assert list1 is not list2   # different objects
    assert nothing is None      # `is` is the correct check for None

    # Mutable aliasing: two names, one object -> edits are shared.
    alias = list1
    alias.append(4)
    assert list1 == [1, 2, 3, 4]  # list1 changed through `alias`

    print("1. types/identity:", x, pi, name, ok, nothing, "| aliasing works")


# ===========================================================================
# 2. TRUTHINESS
# ===========================================================================
def demo_truthiness() -> None:
    falsy = [0, 0.0, "", [], {}, set(), None, False]
    assert all(not bool(v) for v in falsy)
    # Pythonic: `if items:` means "if there are items".
    items: list[int] = []
    assert not items
    items = [1]
    assert items
    print("2. truthiness: empty containers/0/None are falsy")


# ===========================================================================
# 3. CONTROL FLOW
# ===========================================================================
def classify(n: int) -> str:
    # match (Python 3.10+) — structural pattern matching replaces switch.
    match n:
        case 0:
            return "zero"
        case _ if n < 0:
            return "negative"
        case _:
            return "positive"


def first_prime_gap(limit: int) -> str:
    # for-else: the else runs only if the loop finished WITHOUT break.
    for n in range(2, limit):
        if all(n % d for d in range(2, int(n**0.5) + 1)):
            return f"first prime found: {n}"
    else:
        return "no prime found"


def demo_control_flow() -> None:
    assert classify(0) == "zero"
    assert classify(-5) == "negative"
    assert classify(9) == "positive"
    assert "prime" in first_prime_gap(20)
    print("3. control flow:", classify(-1), "|", first_prime_gap(20))


# ===========================================================================
# 4. THE FOUR BUILT-IN COLLECTIONS
# ===========================================================================
def demo_collections() -> None:
    # list — ordered, mutable; comprehension is the Pythonic loop.
    squares = [n * n for n in range(5)]
    evens = [n for n in range(10) if n % 2 == 0]
    assert squares == [0, 1, 4, 9, 16]
    assert evens == [0, 2, 4, 6, 8]

    # tuple — immutable; hashable so it can be a dict key.
    point = (3, 4)
    lookup = {point: "origin-ish"}
    assert lookup[(3, 4)] == "origin-ish"

    # set — O(1) membership, dedupe, set algebra.
    a, b = {1, 2, 3}, {2, 3, 4}
    assert a & b == {2, 3}
    assert a | b == {1, 2, 3, 4}
    assert a - b == {1}
    assert 2 in a  # O(1)

    # dict — key -> value, O(1) lookup, safe access with .get.
    prices = {"apple": 3, "pear": 5}
    assert prices.get("plum", 0) == 0
    assert sorted(prices.items()) == [("apple", 3), ("pear", 5)]

    # collections upgrades
    counts = Counter("mississippi")
    assert counts["s"] == 4
    groups: dict[str, list[int]] = defaultdict(list)
    for n in range(6):
        groups["even" if n % 2 == 0 else "odd"].append(n)
    assert groups["even"] == [0, 2, 4]
    q: deque[int] = deque([1, 2, 3])
    q.appendleft(0)
    assert q.popleft() == 0

    print("4. collections: list/tuple/set/dict + Counter/defaultdict/deque")


# ===========================================================================
# 5. FUNCTIONS
# ===========================================================================
def greet(name: str, greeting: str = "Hi", *args: str, **kwargs: object) -> str:
    extras = f" ({', '.join(args)})" if args else ""
    return f"{greeting}, {name}{extras}"


def add_item(x: int, items: list[int] | None = None) -> list[int]:
    # Correct: avoid the mutable-default trap by defaulting to None.
    items = items if items is not None else []
    items.append(x)
    return items


def demo_functions() -> None:
    assert greet("Ada") == "Hi, Ada"
    assert greet("Ada", "Hello", "eng", "math") == "Hello, Ada (eng, math)"

    # Mutable-default is NOT shared because we guard it.
    assert add_item(1) == [1]
    assert add_item(2) == [2]  # fresh list, no leakage

    double = lambda x: x * 2  # noqa: E731 (illustrative)
    assert double(21) == 42

    # Functional helpers (comprehensions are usually clearer).
    assert list(map(lambda x: x * 2, [1, 2, 3])) == [2, 4, 6]
    assert list(filter(lambda x: x > 1, [1, 2, 3])) == [2, 3]
    assert reduce(lambda acc, n: acc + n, [1, 2, 3, 4], 0) == 10

    print("5. functions: defaults, *args/**kwargs, lambda, map/filter/reduce")


# ===========================================================================
# 6. FILE HANDLING (context managers) + JSON
# ===========================================================================
def demo_files() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "data.txt"
        with open(path, "w", encoding="utf-8") as f:  # auto-closes on exit
            f.write("alpha\nbeta\ngamma\n")

        with open(path, encoding="utf-8") as f:
            lines = [line.strip() for line in f]  # lazy, memory-cheap iteration
        assert lines == ["alpha", "beta", "gamma"]

        cfg_path = Path(d) / "cfg.json"
        cfg_path.write_text(json.dumps({"env": "prod", "workers": 4}))
        cfg = json.loads(cfg_path.read_text())
        assert cfg["workers"] == 4

    print("6. files: with-statement auto-close, JSON round-trip")


# ===========================================================================
# 7. EXCEPTION HANDLING (EAFP)
# ===========================================================================
class PaymentDeclined(Exception):
    """Domain-specific exception communicates a business error."""


def charge(balance: int, amount: int) -> int:
    if amount > balance:
        raise PaymentDeclined(f"need {amount}, have {balance}")
    return balance - amount


def safe_int(value: str, default: int = 0) -> int:
    # EAFP: try the operation, handle the specific failure.
    try:
        return int(value)
    except ValueError:
        return default


def demo_exceptions() -> None:
    assert safe_int("42") == 42
    assert safe_int("nope", default=-1) == -1

    try:
        charge(balance=100, amount=250)
    except PaymentDeclined as e:
        caught = str(e)
    else:  # pragma: no cover - illustrative
        caught = ""
    finally:
        cleanup = True  # `finally` always runs (cleanup)
    assert "need 250" in caught and cleanup
    print("7. exceptions: EAFP, custom exception, try/except/else/finally")


def main() -> None:
    print("=" * 68)
    print("PYTHON FOUNDATIONS — fundamentals.py")
    print("=" * 68)
    demo_types_and_identity()
    demo_truthiness()
    demo_control_flow()
    demo_collections()
    demo_functions()
    demo_files()
    demo_exceptions()
    print("-" * 68)
    print("All fundamentals demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
