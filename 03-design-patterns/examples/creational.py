"""
03 — Design Patterns Catalog: Creational (5)
============================================

Runnable companion to PDF Chapter "3+ — Complete Design Patterns Catalog".

  * Factory Method   — a function/subclass decides WHICH class to build
  * Abstract Factory — families of related objects built together
  * Builder          — step-by-step construction (fluent)
  * Prototype        — clone a configured instance
  * Singleton        — exactly one instance (used sparingly)

Run:  python creational.py
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


# ===========================================================================
# FACTORY METHOD
# ===========================================================================
class JsonRepo:
    kind = "json"


class SqlRepo:
    kind = "sql"


def make_repo(kind: str) -> object:
    """One place decides the concrete class; callers stay ignorant."""
    return {"json": JsonRepo, "sql": SqlRepo}[kind]()


# ===========================================================================
# ABSTRACT FACTORY — swap a whole family at once
# ===========================================================================
class S3:
    name = "s3"


class SQS:
    name = "sqs"


class GCS:
    name = "gcs"


class PubSub:
    name = "pubsub"


class AwsFactory:
    def storage(self) -> object:
        return S3()

    def queue(self) -> object:
        return SQS()


class GcpFactory:
    def storage(self) -> object:
        return GCS()

    def queue(self) -> object:
        return PubSub()


def provision(factory: object) -> tuple[str, str]:
    store = factory.storage()  # type: ignore[attr-defined]
    q = factory.queue()        # type: ignore[attr-defined]
    return store.name, q.name  # type: ignore[attr-defined]


# ===========================================================================
# BUILDER — fluent, order-safe construction
# ===========================================================================
class QueryBuilder:
    def __init__(self) -> None:
        self._select = "*"
        self._table = ""
        self._where: list[str] = []

    def select(self, *cols: str) -> QueryBuilder:
        self._select = ", ".join(cols)
        return self  # returning self enables chaining

    def table(self, name: str) -> QueryBuilder:
        self._table = name
        return self

    def where(self, clause: str) -> QueryBuilder:
        self._where.append(clause)
        return self

    def build(self) -> str:
        sql = f"SELECT {self._select} FROM {self._table}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        return sql


# ===========================================================================
# PROTOTYPE — clone instead of rebuild
# ===========================================================================
@dataclass
class ServerConfig:
    region: str = "us-east-1"
    tags: dict[str, str] = field(default_factory=dict)

    def clone(self) -> ServerConfig:
        return copy.deepcopy(self)  # Python's deepcopy IS Prototype


# ===========================================================================
# SINGLETON — one instance (prefer dependency injection in real code)
# ===========================================================================
class AppConfig:
    _instance: AppConfig | None = None

    def __new__(cls) -> AppConfig:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.settings = {}  # type: ignore[attr-defined]
        return cls._instance


def main() -> None:
    print("=" * 68)
    print("DESIGN PATTERNS — creational.py")
    print("=" * 68)

    assert isinstance(make_repo("json"), JsonRepo)
    assert isinstance(make_repo("sql"), SqlRepo)
    print("Factory Method: kind ->", make_repo("json").kind)  # type: ignore[attr-defined]

    assert provision(AwsFactory()) == ("s3", "sqs")
    assert provision(GcpFactory()) == ("gcs", "pubsub")
    print("Abstract Factory: AWS ->", provision(AwsFactory()))

    sql = QueryBuilder().select("id", "name").table("users").where("age > 18").build()
    assert sql == "SELECT id, name FROM users WHERE age > 18"
    print("Builder:", sql)

    base = ServerConfig(tags={"team": "core"})
    twin = base.clone()
    twin.tags["team"] = "data"
    assert base.tags["team"] == "core"  # deep clone: independent
    print("Prototype: clone is independent ->", base.tags, twin.tags)

    a, b = AppConfig(), AppConfig()
    a.settings["x"] = 1  # type: ignore[attr-defined]
    assert a is b and b.settings["x"] == 1  # type: ignore[attr-defined]
    print("Singleton: same instance shared")

    print("-" * 68)
    print("All creational-pattern demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
