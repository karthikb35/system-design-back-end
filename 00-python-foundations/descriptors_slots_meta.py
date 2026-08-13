"""
00 — Python Mastery: Descriptors, __slots__, Decorators-with-args & Metaclasses
==============================================================================

Runnable companion to PDF Book I "Advanced Python — how classes really work".

These are the "how does Python itself work?" features senior interviews probe:

  * DESCRIPTORS  — objects with __get__/__set__ that control attribute access.
                   This is the machinery behind @property, methods, classmethod,
                   staticmethod, and ORM fields. We build a validating one.
  * __slots__    — trade the per-instance __dict__ for a fixed set of fields:
                   less memory, faster access, no accidental new attributes.
  * DECORATOR    — a decorator that TAKES ARGUMENTS (a 3-level nesting) plus a
    FACTORY        class-based decorator; the general pattern behind retry(n),
                   lru_cache(maxsize=...), app.get("/path"), etc.
  * METACLASS    — a class whose instances are classes; customizes class
                   CREATION. We build a registry metaclass (the plugin pattern).
"""

import functools


# --------------------------------------------------------------------------
# DESCRIPTOR: reusable, validating managed attribute. __set_name__ learns the
# attribute name automatically; __get__/__set__ intercept access on instances.
# --------------------------------------------------------------------------
class Positive:
    """A data descriptor that rejects non-positive numbers."""

    def __set_name__(self, owner, name):
        self._name = "_" + name         # where we stash the real value

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self                 # accessed on the class, not an instance
        return getattr(obj, self._name)

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self._name[1:]} must be positive, got {value}")
        setattr(obj, self._name, value)


class Product:
    price = Positive()                  # the descriptor manages `price`
    quantity = Positive()

    def __init__(self, price, quantity):
        self.price = price              # goes through Positive.__set__ (validates)
        self.quantity = quantity

    @property                           # @property is itself a descriptor
    def total(self):
        return self.price * self.quantity


def descriptor_demo() -> None:
    p = Product(price=10, quantity=3)
    assert p.total == 30                # @property computed attribute
    p.price = 20                        # validated on assignment
    assert p.total == 60
    for bad in (0, -5):
        try:
            Product(price=bad, quantity=1)
            raise AssertionError("should have rejected")
        except ValueError:
            pass
    print("   descriptor: one Positive() class validates every field it manages (DRY)")


# --------------------------------------------------------------------------
# __slots__: fixed fields, no __dict__. Saves memory at scale and blocks typos.
# --------------------------------------------------------------------------
class Slotted:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


class Dicted:
    def __init__(self, x, y):
        self.x, self.y = x, y


def slots_demo() -> None:
    s = Slotted(1, 2)
    assert (s.x, s.y) == (1, 2)
    assert not hasattr(s, "__dict__")   # slots removed the per-instance dict
    try:
        s.z = 3                          # assigning an unknown attr is blocked
        raise AssertionError("slots should forbid new attributes")
    except AttributeError:
        pass
    d = Dicted(1, 2)
    d.z = 3                              # a normal class silently accepts typos
    assert d.__dict__ == {"x": 1, "y": 2, "z": 3}
    print("   __slots__: no per-instance __dict__ -> less memory, and typos raise instead of hiding")


# --------------------------------------------------------------------------
# DECORATOR WITH ARGUMENTS: three nested functions -> deco(args)(fn)(*call).
# --------------------------------------------------------------------------
def retry(times: int):
    """Retry the wrapped function up to `times` attempts on exception."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last = None
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:   # noqa: BLE001 - demo
                    last = e
            raise last
        return wrapper

    return decorator


def retry_demo() -> None:
    calls = {"n": 0}

    @retry(times=3)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("try again")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3              # failed twice, succeeded on the third
    assert flaky.__name__ == "flaky"   # functools.wraps preserved identity
    print("   decorator-with-args: retry(times=3) is deco(args)(fn)(*call) — three layers")


# --------------------------------------------------------------------------
# METACLASS: customize class CREATION. Here: auto-register every subclass in a
# registry (the plugin pattern) without the subclass writing any boilerplate.
# --------------------------------------------------------------------------
class PluginRegistry(type):
    registry = {}

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if bases:                        # skip the base class itself
            PluginRegistry.registry[name.lower()] = cls
        return cls


class Plugin(metaclass=PluginRegistry):
    pass


class JsonExporter(Plugin):
    def run(self):
        return "json"


class CsvExporter(Plugin):
    def run(self):
        return "csv"


def metaclass_demo() -> None:
    # Both subclasses registered themselves automatically at definition time.
    assert set(PluginRegistry.registry) == {"jsonexporter", "csvexporter"}
    exporter = PluginRegistry.registry["jsonexporter"]()
    assert exporter.run() == "json"
    print("   metaclass: subclasses auto-register at creation — the plugin pattern, zero boilerplate")


def main() -> None:
    print("=" * 70)
    print("PYTHON MASTERY — descriptors_slots_meta.py")
    print("=" * 70)
    print("1. Descriptors (the machinery behind @property/ORM fields):")
    descriptor_demo()
    print("2. __slots__ (memory + typo protection):")
    slots_demo()
    print("3. Decorator with arguments (3-level nesting):")
    retry_demo()
    print("4. Metaclass (customize class creation -> auto-registry):")
    metaclass_demo()
    print("-" * 70)
    print("All descriptors_slots_meta demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
