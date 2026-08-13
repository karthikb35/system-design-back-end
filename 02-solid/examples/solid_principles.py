"""
02 — SOLID Principles, One Focused Before/After Each
===================================================

Runnable companion to PDF Book IV "The five principles that make OO code change-friendly".

SOLID is not dogma — it's five levers for LOW COUPLING and HIGH COHESION so that
change stays cheap. This file demonstrates each principle with the smallest
honest "smell → fix" pair, and asserts the fixed design actually behaves:

    S  Single Responsibility  — one reason to change per class
    O  Open/Closed            — extend without editing tested code
    L  Liskov Substitution    — subtypes must honor the base type's contract
    I  Interface Segregation  — many small roles beat one fat interface
    D  Dependency Inversion   — depend on abstractions, inject concretions

Run:  python solid_principles.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


# ===========================================================================
# S — SINGLE RESPONSIBILITY: split "compute" from "format" from "persist"
# ===========================================================================
# SMELL: a Report class that calculates totals, renders HTML, AND saves files
# changes for three unrelated reasons. Split it so each class has ONE job.
class SalesReport:
    def __init__(self, sales: list[float]):
        self.sales = sales

    def total(self) -> float:                 # the ONLY reason this class changes
        return sum(self.sales)


class HtmlReportFormatter:
    def render(self, report: SalesReport) -> str:   # formatting is a separate axis
        return f"<h1>Total: {report.total():.2f}</h1>"


class ReportRepository:
    def __init__(self):
        self.saved: dict[str, str] = {}

    def save(self, name: str, content: str) -> None:  # persistence is a third axis
        self.saved[name] = content


# ===========================================================================
# O — OPEN/CLOSED: add behavior by adding a class, not editing an if-ladder
# ===========================================================================
# SMELL: `if shape == "circle": ... elif "square": ...` — every new shape edits
# a tested function. FIX: a polymorphic type; new shapes are NEW classes.
class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...


class Circle(Shape):
    def __init__(self, r: float): self.r = r
    def area(self) -> float: return 3.14159 * self.r * self.r


class Square(Shape):
    def __init__(self, s: float): self.s = s
    def area(self) -> float: return self.s * self.s


class Triangle(Shape):                         # added WITHOUT touching total_area
    def __init__(self, b: float, h: float): self.b, self.h = b, h
    def area(self) -> float: return 0.5 * self.b * self.h


def total_area(shapes: list[Shape]) -> float:  # closed for modification
    return sum(s.area() for s in shapes)       # open for extension (new Shape)


# ===========================================================================
# L — LISKOV SUBSTITUTION: a subtype must be usable wherever the base is
# ===========================================================================
# SMELL: the classic Square(Rectangle) — overriding width to also set height
# breaks code that trusts Rectangle's contract. FIX: model them as siblings so
# no subtype weakens a base guarantee.
class Rectangle:
    def __init__(self, w: float, h: float): self._w, self._h = w, h
    def area(self) -> float: return self._w * self._h


class SquareLSP:
    def __init__(self, side: float): self._s = side
    def area(self) -> float: return self._s * self._s


def area_of(shape) -> float:                   # works for BOTH; neither surprises
    return shape.area()


# ===========================================================================
# I — INTERFACE SEGREGATION: don't force clients to implement methods they skip
# ===========================================================================
# SMELL: one Worker interface with work() AND eat() forces a RobotWorker to
# implement a meaningless eat(). FIX: split into focused roles (Protocols).
class Workable(Protocol):
    def work(self) -> str: ...


class Eatable(Protocol):
    def eat(self) -> str: ...


class Human:                                   # implements BOTH roles
    def work(self) -> str: return "coding"
    def eat(self) -> str: return "lunch"


class Robot:                                   # implements ONLY what it needs
    def work(self) -> str: return "welding"


def run_shift(workers: list[Workable]) -> list[str]:
    return [w.work() for w in workers]         # asks only for Workable


# ===========================================================================
# D — DEPENDENCY INVERSION: high-level policy depends on an abstraction
# ===========================================================================
# SMELL: OrderService constructs a concrete MySqlDatabase inside itself — you
# can't test it without a real DB and can't swap stores. FIX: depend on a
# NotificationGateway abstraction and INJECT the concrete one.
class NotificationGateway(Protocol):
    def send(self, to: str, msg: str) -> None: ...


class EmailGateway:
    def __init__(self): self.sent: list[tuple[str, str]] = []
    def send(self, to: str, msg: str) -> None: self.sent.append((to, msg))


class SmsGateway:
    def __init__(self): self.sent: list[tuple[str, str]] = []
    def send(self, to: str, msg: str) -> None: self.sent.append((to, msg))


class OrderService:
    def __init__(self, gateway: NotificationGateway):   # inject the abstraction
        self._gateway = gateway

    def place(self, customer: str) -> None:
        self._gateway.send(customer, "Order confirmed")  # no idea which concrete


def demo() -> None:
    # S — each class does one job and composes cleanly.
    report = SalesReport([100.0, 250.0, 50.0])
    html = HtmlReportFormatter().render(report)
    repo = ReportRepository()
    repo.save("q1", html)
    assert report.total() == 400.0
    assert "400.00" in html and repo.saved["q1"] == html
    print("   S · SalesReport / Formatter / Repository each change for one reason")

    # O — add Triangle without editing total_area.
    shapes: list[Shape] = [Circle(1), Square(2), Triangle(3, 4)]
    assert round(total_area(shapes), 2) == round(3.14159 + 4 + 6, 2)
    print("   O · total_area unchanged; Triangle added as a new class")

    # L — both shapes are substitutable in area_of with no surprises.
    assert area_of(Rectangle(3, 4)) == 12
    assert area_of(SquareLSP(5)) == 25
    print("   L · Rectangle and SquareLSP each honor the area() contract")

    # I — Robot needn't implement eat(); run_shift only needs Workable.
    assert run_shift([Human(), Robot()]) == ["coding", "welding"]
    print("   I · Robot implements only work(); no dead eat() method forced")

    # D — same service, swap the injected gateway with zero changes.
    email = EmailGateway()
    OrderService(email).place("ada@example.com")
    sms = SmsGateway()
    OrderService(sms).place("+15551234")
    assert email.sent == [("ada@example.com", "Order confirmed")]
    assert sms.sent == [("+15551234", "Order confirmed")]
    print("   D · OrderService depends on the gateway abstraction; concretion injected")


def main() -> None:
    print("=" * 70)
    print("SOLID — solid_principles.py")
    print("=" * 70)
    print("Five levers for low coupling / high cohesion (smell -> fix):")
    demo()
    print("-" * 70)
    print("Lesson: SOLID exists to keep CHANGE cheap — apply it where change actually happens, not everywhere.")
    print("All solid_principles demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
