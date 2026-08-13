"""
00 — Python Mastery: Advanced Dunder (Magic) Methods
====================================================

Runnable companion to PDF Book I "Advanced Python — the data model".

Dunder ("double underscore") methods are how your objects plug into Python's
built-in syntax. Implement them and your class behaves like a native type:
it prints nicely, compares, hashes, iterates, indexes, works in `with`, and
can even be called like a function. Each demo below is self-checking.

Covered:
  * __repr__ / __str__      — developer vs user string
  * __eq__ / __hash__       — value equality + usability as a dict/set key
  * __lt__ (+ total_ordering) — ordering/sorting
  * __len__ / __getitem__ / __contains__ — behave like a container
  * __iter__ / __next__     — be iterable in a for-loop
  * __enter__ / __exit__    — be a context manager
  * __call__                — be callable like a function
  * __getattr__             — dynamic attribute fallback
  * __add__                 — operator overloading
"""

from functools import total_ordering


# --------------------------------------------------------------------------
# __repr__/__str__, __eq__/__hash__, ordering — a well-behaved value object.
# --------------------------------------------------------------------------
@total_ordering
class Money:
    """An immutable value object: two Moneys are equal by value and orderable."""

    __slots__ = ("cents",)  # (also demonstrates slots: no per-instance __dict__)

    def __init__(self, dollars: float):
        object.__setattr__(self, "cents", round(dollars * 100))

    # developer-facing, unambiguous; ideally eval-able
    def __repr__(self) -> str:
        return f"Money({self.cents / 100:.2f})"

    # user-facing, pretty
    def __str__(self) -> str:
        return f"${self.cents / 100:,.2f}"

    # value equality — two Money with same cents are equal
    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and self.cents == other.cents

    # equal objects MUST hash equal -> safe as dict/set keys
    def __hash__(self) -> int:
        return hash(self.cents)

    # total_ordering derives <=, >, >= from __eq__ + __lt__
    def __lt__(self, other) -> bool:
        return self.cents < other.cents

    # operator overloading
    def __add__(self, other) -> "Money":
        return Money((self.cents + other.cents) / 100)


def dunder_value_object() -> None:
    a, b = Money(19.99), Money(19.99)
    assert a == b                      # __eq__
    assert hash(a) == hash(b)          # equal -> same hash
    assert {a} == {b}                  # usable as set members
    assert Money(5) < Money(10)        # __lt__
    assert Money(10) >= Money(10)      # derived by total_ordering
    assert sorted([Money(3), Money(1), Money(2)]) == [Money(1), Money(2), Money(3)]
    assert (Money(1.50) + Money(2.50)) == Money(4.00)   # __add__
    assert repr(Money(4)) == "Money(4.00)"
    assert str(Money(1234.5)) == "$1,234.50"
    print("   value object: __repr__/__eq__/__hash__/__lt__/__add__ all behave natively")


# --------------------------------------------------------------------------
# Container protocol: __len__, __getitem__, __contains__, __iter__.
# --------------------------------------------------------------------------
class Playlist:
    def __init__(self, songs):
        self._songs = list(songs)

    def __len__(self):
        return len(self._songs)

    def __getitem__(self, i):          # enables indexing AND slicing AND iteration
        return self._songs[i]

    def __contains__(self, song):      # enables `in`
        return song in self._songs


def dunder_container() -> None:
    p = Playlist(["a", "b", "c", "d"])
    assert len(p) == 4                 # __len__
    assert p[0] == "a"                 # __getitem__
    assert p[1:3] == ["b", "c"]        # slicing via __getitem__
    assert "c" in p                    # __contains__
    assert [s.upper() for s in p] == ["A", "B", "C", "D"]  # iterable via __getitem__
    print("   container: len(), indexing, slicing, `in`, and iteration all work")


# --------------------------------------------------------------------------
# Iterator protocol: __iter__ returns an object with __next__.
# --------------------------------------------------------------------------
class Countdown:
    def __init__(self, start: int):
        self.start = start

    def __iter__(self):
        self._n = self.start
        return self

    def __next__(self):
        if self._n <= 0:
            raise StopIteration
        self._n -= 1
        return self._n + 1


def dunder_iterator() -> None:
    assert list(Countdown(3)) == [3, 2, 1]
    got = [n for n in Countdown(5)]
    assert got == [5, 4, 3, 2, 1]
    print("   iterator: __iter__/__next__ drive a real for-loop (StopIteration ends it)")


# --------------------------------------------------------------------------
# Context manager: __enter__/__exit__ guarantee cleanup even on exceptions.
# --------------------------------------------------------------------------
class Transaction:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        self.log.append("BEGIN")
        return self

    def __exit__(self, exc_type, exc, tb):
        # returning False re-raises any exception; we roll back on error
        self.log.append("ROLLBACK" if exc_type else "COMMIT")
        return False


def dunder_context_manager() -> None:
    log = []
    with Transaction(log):
        log.append("work")
    assert log == ["BEGIN", "work", "COMMIT"]

    log2 = []
    try:
        with Transaction(log2):
            log2.append("work")
            raise ValueError("boom")
    except ValueError:
        pass
    assert log2 == ["BEGIN", "work", "ROLLBACK"]   # cleanup ran despite the error
    print("   context manager: __enter__/__exit__ commit on success, roll back on error")


# --------------------------------------------------------------------------
# __call__ (callable instances) and __getattr__ (dynamic fallback).
# --------------------------------------------------------------------------
class Multiplier:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, x):             # instance behaves like a function
        return x * self.factor


class Config:
    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):       # only called when normal lookup FAILS
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name) from None


def dunder_callable_and_getattr() -> None:
    triple = Multiplier(3)
    assert triple(10) == 30            # __call__
    assert callable(triple)
    cfg = Config({"host": "localhost", "port": 5432})
    assert cfg.host == "localhost"     # __getattr__ fallback into the dict
    assert cfg.port == 5432
    try:
        _ = cfg.missing
        raise AssertionError("should have raised")
    except AttributeError:
        pass
    print("   __call__: instances act like functions; __getattr__: dynamic attribute access")


def main() -> None:
    print("=" * 68)
    print("PYTHON MASTERY — advanced_dunder.py")
    print("=" * 68)
    print("1. Value object (repr/eq/hash/ordering/add):")
    dunder_value_object()
    print("2. Container protocol (len/getitem/contains/iter):")
    dunder_container()
    print("3. Iterator protocol (iter/next):")
    dunder_iterator()
    print("4. Context manager (enter/exit):")
    dunder_context_manager()
    print("5. Callable + dynamic attributes (call/getattr):")
    dunder_callable_and_getattr()
    print("-" * 68)
    print("All advanced_dunder demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
