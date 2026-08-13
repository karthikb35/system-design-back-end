"""
03 — Design Patterns Catalog: Behavioral (11)
=============================================

Runnable companion to PDF Chapter "3+ — Complete Design Patterns Catalog".

  * Chain of Responsibility — pass a request along handlers
  * Command                 — a request captured as an object (undo/queue)
  * Interpreter             — evaluate a tiny grammar
  * Iterator                — traverse without exposing internals
  * Mediator                — centralize many-to-many communication
  * Memento                 — snapshot & restore state
  * Observer                — notify dependents on change
  * State                   — behavior changes with internal state
  * Strategy                — interchangeable algorithms
  * Template Method         — fixed skeleton, overridable steps
  * Visitor                 — add operations without changing element classes

Run:  python behavioral.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Callable, Protocol


# ===========================================================================
# CHAIN OF RESPONSIBILITY
# ===========================================================================
class Handler:
    def __init__(self, name: str, can_handle: Callable[[str], bool],
                 nxt: "Handler | None" = None) -> None:
        self.name, self.can_handle, self.nxt = name, can_handle, nxt

    def handle(self, req: str) -> str:
        if self.can_handle(req):
            return f"{self.name} handled {req}"
        if self.nxt:
            return self.nxt.handle(req)  # pass along the chain
        return "unhandled"


# ===========================================================================
# COMMAND
# ===========================================================================
class Command(Protocol):
    def execute(self) -> None: ...
    def undo(self) -> None: ...


class AddItem:
    def __init__(self, cart: list[str], item: str) -> None:
        self.cart, self.item = cart, item

    def execute(self) -> None:
        self.cart.append(self.item)

    def undo(self) -> None:
        self.cart.remove(self.item)


# ===========================================================================
# INTERPRETER — evaluate "3 + 4 - 1"
# ===========================================================================
def interpret(expr: str) -> int:
    tokens = expr.split()
    total = int(tokens[0])
    i = 1
    while i < len(tokens):
        op, num = tokens[i], int(tokens[i + 1])
        total = total + num if op == "+" else total - num
        i += 2
    return total


# ===========================================================================
# ITERATOR
# ===========================================================================
class Ring:
    """Custom collection exposing an iterator without revealing its storage."""

    def __init__(self, items: list[int]) -> None:
        self._items = items

    def __iter__(self) -> Iterator[int]:
        yield from self._items  # generator = an iterator


# ===========================================================================
# MEDIATOR
# ===========================================================================
class ChatRoom:
    def __init__(self) -> None:
        self.log: list[str] = []

    def send(self, sender: str, msg: str) -> None:
        self.log.append(f"{sender}: {msg}")  # hub routes all messages


class User:
    def __init__(self, name: str, room: ChatRoom) -> None:
        self.name, self.room = name, room

    def say(self, msg: str) -> None:
        self.room.send(self.name, msg)  # users never reference each other


# ===========================================================================
# MEMENTO
# ===========================================================================
class Editor:
    def __init__(self) -> None:
        self.text = ""

    def save(self) -> str:  # produce a memento
        return self.text

    def restore(self, memento: str) -> None:  # roll back (undo)
        self.text = memento


# ===========================================================================
# OBSERVER
# ===========================================================================
class Subject:
    def __init__(self) -> None:
        self._observers: list[Callable[[str], None]] = []

    def subscribe(self, fn: Callable[[str], None]) -> None:
        self._observers.append(fn)

    def notify(self, event: str) -> None:
        for fn in self._observers:
            fn(event)  # source doesn't know who reacts


# ===========================================================================
# STATE — order lifecycle without an if/elif ladder
# ===========================================================================
class OrderState(ABC):
    @abstractmethod
    def next(self) -> "OrderState": ...
    @property
    @abstractmethod
    def name(self) -> str: ...


class Pending(OrderState):
    name = "pending"

    def next(self) -> OrderState:
        return Paid()


class Paid(OrderState):
    name = "paid"

    def next(self) -> OrderState:
        return Shipped()


class Shipped(OrderState):
    name = "shipped"

    def next(self) -> OrderState:
        return self  # terminal


class Order:
    def __init__(self) -> None:
        self.state: OrderState = Pending()

    def advance(self) -> None:
        self.state = self.state.next()


# ===========================================================================
# STRATEGY
# ===========================================================================
class PricingStrategy(Protocol):
    def price(self, base: int) -> int: ...


class NoDiscount:
    def price(self, base: int) -> int:
        return base


class TenPercentOff:
    def price(self, base: int) -> int:
        return base * 90 // 100


def checkout(base: int, strategy: PricingStrategy) -> int:
    return strategy.price(base)  # algorithm chosen at runtime


# ===========================================================================
# TEMPLATE METHOD
# ===========================================================================
class ETLJob(ABC):
    def run(self) -> list[str]:  # the fixed skeleton
        return self.load(self.transform(self.extract()))

    def extract(self) -> list[str]:
        return ["a", "b", "c"]

    @abstractmethod
    def transform(self, rows: list[str]) -> list[str]: ...

    def load(self, rows: list[str]) -> list[str]:
        return rows


class UppercaseETL(ETLJob):
    def transform(self, rows: list[str]) -> list[str]:
        return [r.upper() for r in rows]  # only this step changes


# ===========================================================================
# VISITOR — new operation over a fixed set of node types
# ===========================================================================
class Num:
    def __init__(self, value: int) -> None:
        self.value = value

    def accept(self, visitor: "Visitor") -> int:
        return visitor.visit_num(self)


class Add:
    def __init__(self, left: object, right: object) -> None:
        self.left, self.right = left, right

    def accept(self, visitor: "Visitor") -> int:
        return visitor.visit_add(self)


class Visitor(Protocol):
    def visit_num(self, node: Num) -> int: ...
    def visit_add(self, node: Add) -> int: ...


class Evaluator:
    def visit_num(self, node: Num) -> int:
        return node.value

    def visit_add(self, node: Add) -> int:
        return node.left.accept(self) + node.right.accept(self)  # type: ignore[attr-defined]


def main() -> None:
    print("=" * 68)
    print("DESIGN PATTERNS — behavioral.py")
    print("=" * 68)

    chain = Handler("auth", lambda r: r == "login",
                    Handler("data", lambda r: r == "query"))
    assert chain.handle("query") == "data handled query"
    assert chain.handle("unknown") == "unhandled"
    print("Chain of Responsibility:", chain.handle("query"))

    cart: list[str] = []
    cmd: Command = AddItem(cart, "book")
    cmd.execute(); assert cart == ["book"]
    cmd.undo(); assert cart == []
    print("Command: execute then undo")

    assert interpret("3 + 4 - 1") == 6
    print("Interpreter: '3 + 4 - 1' ->", interpret("3 + 4 - 1"))

    assert list(Ring([1, 2, 3])) == [1, 2, 3]
    print("Iterator: custom Ring iterates 1,2,3")

    room = ChatRoom()
    User("ada", room).say("hi")
    User("bob", room).say("yo")
    assert room.log == ["ada: hi", "bob: yo"]
    print("Mediator:", room.log)

    ed = Editor()
    ed.text = "v1"
    snapshot = ed.save()
    ed.text = "v2"
    ed.restore(snapshot)
    assert ed.text == "v1"
    print("Memento: restored to 'v1'")

    seen: list[str] = []
    subj = Subject()
    subj.subscribe(seen.append)
    subj.notify("OrderPlaced")
    assert seen == ["OrderPlaced"]
    print("Observer: subscriber received 'OrderPlaced'")

    order = Order()
    states = [order.state.name]
    for _ in range(3):
        order.advance()
        states.append(order.state.name)
    assert states == ["pending", "paid", "shipped", "shipped"]
    print("State:", " -> ".join(states))

    assert checkout(100, NoDiscount()) == 100
    assert checkout(100, TenPercentOff()) == 90
    print("Strategy: 100 with 10%% off ->", checkout(100, TenPercentOff()))

    assert UppercaseETL().run() == ["A", "B", "C"]
    print("Template Method: ETL ->", UppercaseETL().run())

    tree = Add(Num(3), Add(Num(4), Num(5)))
    assert tree.accept(Evaluator()) == 12
    print("Visitor: evaluate (3 + (4 + 5)) ->", tree.accept(Evaluator()))

    print("-" * 68)
    print("All behavioral-pattern demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
