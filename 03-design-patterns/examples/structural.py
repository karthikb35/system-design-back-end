"""
03 — Design Patterns Catalog: Structural (7)
============================================

Runnable companion to PDF Chapter "3+ — Complete Design Patterns Catalog".

  * Adapter    — make an incompatible interface fit
  * Bridge     — split abstraction from implementation (avoid class explosion)
  * Composite  — treat leaves and groups uniformly (a tree)
  * Decorator  — add behavior by wrapping, same interface
  * Facade     — one simple entry point over a complex subsystem
  * Flyweight  — share common state to save memory
  * Proxy      — a stand-in that controls access (lazy/cached/secured)

Run:  python structural.py
"""

from __future__ import annotations

from typing import Protocol


# ===========================================================================
# ADAPTER — wrap a 3rd-party shape behind YOUR interface
# ===========================================================================
class Notifier(Protocol):
    def send(self, msg: str) -> str: ...


class LegacySmsSdk:  # third-party, "wrong" method name
    def dispatch_text(self, body: str) -> str:
        return f"SMS:{body}"


class SmsAdapter:
    def __init__(self, sdk: LegacySmsSdk) -> None:
        self._sdk = sdk

    def send(self, msg: str) -> str:  # adapts dispatch_text -> send
        return self._sdk.dispatch_text(msg)


# ===========================================================================
# BRIDGE — abstraction (Notification) x implementation (Sender)
# ===========================================================================
class Sender(Protocol):
    def deliver(self, payload: str) -> str: ...


class EmailSender:
    def deliver(self, payload: str) -> str:
        return f"email<{payload}>"


class PushSender:
    def deliver(self, payload: str) -> str:
        return f"push<{payload}>"


class Notification:
    def __init__(self, sender: Sender) -> None:
        self.sender = sender  # the "bridge" to the implementation


class Alert(Notification):
    def send(self, msg: str) -> str:
        return self.sender.deliver(f"ALERT:{msg}")


# ===========================================================================
# COMPOSITE — files and folders share total()
# ===========================================================================
class File:
    def __init__(self, size: int) -> None:
        self.size = size

    def total(self) -> int:
        return self.size


class Folder:
    def __init__(self) -> None:
        self.children: list[File | "Folder"] = []

    def add(self, node: File | "Folder") -> "Folder":
        self.children.append(node)
        return self

    def total(self) -> int:
        return sum(c.total() for c in self.children)  # same call on leaf or branch


# ===========================================================================
# DECORATOR — wrap to add behavior, keep the interface
# ===========================================================================
class Service(Protocol):
    def handle(self) -> str: ...


class CoreService:
    def handle(self) -> str:
        return "core"


class LoggingDecorator:
    def __init__(self, wrapped: Service) -> None:
        self.wrapped = wrapped
        self.calls = 0

    def handle(self) -> str:
        self.calls += 1  # added behavior
        return self.wrapped.handle()


# ===========================================================================
# FACADE — hide a complex subsystem behind one call
# ===========================================================================
class _Inventory:
    def reserve(self, sku: str) -> bool:
        return True


class _Payment:
    def charge(self, cents: int) -> bool:
        return cents > 0


class _Shipping:
    def schedule(self, sku: str) -> str:
        return f"ship:{sku}"


class OrderFacade:
    def __init__(self) -> None:
        self._inv, self._pay, self._ship = _Inventory(), _Payment(), _Shipping()

    def place_order(self, sku: str, cents: int) -> str:
        assert self._inv.reserve(sku) and self._pay.charge(cents)
        return self._ship.schedule(sku)  # caller sees ONE method


# ===========================================================================
# FLYWEIGHT — share immutable intrinsic state
# ===========================================================================
class GlyphFactory:
    def __init__(self) -> None:
        self._pool: dict[str, "Glyph"] = {}

    def get(self, char: str) -> "Glyph":
        if char not in self._pool:
            self._pool[char] = Glyph(char)  # created once, shared everywhere
        return self._pool[char]


class Glyph:
    def __init__(self, char: str) -> None:
        self.char = char


# ===========================================================================
# PROXY — control access (here: lazy loading + caching)
# ===========================================================================
class ExpensiveReport:
    def __init__(self) -> None:
        self.data = "…big report…"  # imagine this is slow to build


class ReportProxy:
    def __init__(self) -> None:
        self._real: ExpensiveReport | None = None
        self.build_count = 0

    def data(self) -> str:
        if self._real is None:  # build on first access only
            self._real = ExpensiveReport()
            self.build_count += 1
        return self._real.data


def main() -> None:
    print("=" * 68)
    print("DESIGN PATTERNS — structural.py")
    print("=" * 68)

    adapter: Notifier = SmsAdapter(LegacySmsSdk())
    assert adapter.send("hi") == "SMS:hi"
    print("Adapter:", adapter.send("hi"))

    assert Alert(EmailSender()).send("disk") == "email<ALERT:disk>"
    assert Alert(PushSender()).send("disk") == "push<ALERT:disk>"
    print("Bridge: same Alert over email & push")

    root = Folder().add(File(100)).add(Folder().add(File(20)).add(File(30)))
    assert root.total() == 150
    print("Composite: nested folder total =", root.total())

    deco = LoggingDecorator(CoreService())
    assert deco.handle() == "core" and deco.calls == 1
    print("Decorator: wrapped core, logged calls =", deco.calls)

    assert OrderFacade().place_order("book-1", 4999) == "ship:book-1"
    print("Facade: place_order -> ship:book-1")

    gf = GlyphFactory()
    assert gf.get("a") is gf.get("a")  # shared instance
    print("Flyweight: 'a' shares one instance")

    proxy = ReportProxy()
    proxy.data(); proxy.data()
    assert proxy.build_count == 1  # built once, then cached
    print("Proxy: expensive report built once, cached thereafter")

    print("-" * 68)
    print("All structural-pattern demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
