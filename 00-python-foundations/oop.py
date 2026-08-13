"""
00 — Python Foundations: Object-Oriented Programming
====================================================

Runnable companion to PDF Chapter "P+ — Python Foundations" (OOP section).

Demonstrates the four pillars and Python's data model:
  * Encapsulation   — bundle state with the methods that guard it
  * Abstraction     — expose *what*, hide *how* (ABCs)
  * Inheritance     — reuse + specialize a base class
  * Polymorphism    — same call, different behavior
  * Dunder methods  — make your objects feel built-in
  * dataclasses     — auto-generate boilerplate

Run:  python oop.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ===========================================================================
# ENCAPSULATION — hide internals behind methods that enforce invariants
# ===========================================================================
class BankAccount:
    def __init__(self, balance: int = 0) -> None:
        self._balance = balance  # `_` = "private by convention"

    @property
    def balance(self) -> int:  # read-only view via @property
        return self._balance

    def deposit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("deposit must be positive")
        self._balance += amount

    def withdraw(self, amount: int) -> None:
        if amount > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount


# ===========================================================================
# ABSTRACTION + INHERITANCE + POLYMORPHISM
# ===========================================================================
class Animal(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def speak(self) -> str:  # subclasses MUST implement — the abstraction
        ...

    def introduce(self) -> str:
        return f"{self.name} says {self.speak()}"


class Dog(Animal):
    def speak(self) -> str:  # overrides base -> polymorphism
        return "Woof"


class Cat(Animal):
    def speak(self) -> str:
        return "Meow"


# ===========================================================================
# DUNDER (MAGIC) METHODS + OPERATOR OVERLOADING
# ===========================================================================
@dataclass  # auto-generates __init__, __repr__, __eq__
class Point:
    x: int
    y: int

    def __add__(self, other: Point) -> Point:  # enables Point + Point
        return Point(self.x + other.x, self.y + other.y)

    def __len__(self) -> int:  # enables len(point) -> manhattan distance
        return abs(self.x) + abs(self.y)


@dataclass
class Stack:
    """Shows __len__, __getitem__, __iter__, __bool__ making a class native."""

    _items: list[int] = field(default_factory=list)

    def push(self, v: int) -> None:
        self._items.append(v)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, i: int) -> int:
        return self._items[i]

    def __bool__(self) -> bool:
        return bool(self._items)


# classmethod / staticmethod
class Temperature:
    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    @classmethod
    def from_fahrenheit(cls, f: float) -> Temperature:  # alternative constructor
        return cls((f - 32) * 5 / 9)

    @staticmethod
    def is_freezing(celsius: float) -> bool:  # utility, no self/cls needed
        return celsius <= 0


def main() -> None:
    print("=" * 68)
    print("PYTHON FOUNDATIONS — oop.py")
    print("=" * 68)

    acct = BankAccount(100)
    acct.deposit(50)
    acct.withdraw(30)
    assert acct.balance == 120
    try:
        acct.withdraw(10_000)
    except ValueError as e:
        assert "insufficient" in str(e)
    print("encapsulation:", acct.balance, "(guarded by deposit/withdraw)")

    animals: list[Animal] = [Dog("Rex"), Cat("Mia")]
    speeches = [a.introduce() for a in animals]  # same call, different behavior
    assert speeches == ["Rex says Woof", "Mia says Meow"]
    print("polymorphism:", speeches)

    p = Point(1, 2) + Point(3, 4)
    assert p == Point(4, 6) and len(p) == 10
    print("dunder:", p, "| len(p) =", len(p))

    s = Stack()
    s.push(1)
    s.push(2)
    assert len(s) == 2 and s[0] == 1 and bool(s) is True
    print("dunder container: len/getitem/bool work on Stack")

    t = Temperature.from_fahrenheit(32)
    assert abs(t.celsius) < 1e-9 and Temperature.is_freezing(t.celsius)
    print("class/staticmethod: 32F ->", round(t.celsius, 2), "C (freezing)")

    print("-" * 68)
    print("All OOP demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
