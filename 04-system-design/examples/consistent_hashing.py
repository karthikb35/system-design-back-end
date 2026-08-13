"""
04 — System Design: Consistent Hashing (the ring behind sharding & caches)
==========================================================================

Runnable companion to PDF Book V "How do you shard data across N servers?".

The naive way to map a key to one of N servers is `hash(key) % N`. It works —
until N changes. Add or remove one server and (N → N±1) remaps ALMOST EVERY
key, so every cache misses and every shard reshuffles at once: a stampede.

CONSISTENT HASHING fixes this. Servers and keys are placed on the same circular
hash space [0, 2^32). A key belongs to the first server clockwise from it. Add
or remove a server and only the keys in ONE arc move — about 1/N of them.

VIRTUAL NODES (replicas per server) smooth out the otherwise-lumpy distribution.

This file builds the ring and PROVES that removing a node remaps only ~1/N of
keys, versus ~all of them for modulo hashing.
"""

from __future__ import annotations

import bisect
import hashlib


def _hash(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


class ConsistentHashRing:
    def __init__(self, vnodes: int = 100):
        self._vnodes = vnodes
        self._ring: dict[int, str] = {}     # point on ring -> server
        self._sorted: list[int] = []        # sorted ring points for bisect

    def add(self, server: str) -> None:
        for i in range(self._vnodes):
            point = _hash(f"{server}#{i}")  # virtual node
            self._ring[point] = server
            bisect.insort(self._sorted, point)

    def remove(self, server: str) -> None:
        for i in range(self._vnodes):
            point = _hash(f"{server}#{i}")
            del self._ring[point]
            self._sorted.remove(point)

    def get(self, key: str) -> str:
        if not self._sorted:
            raise KeyError("ring is empty")
        h = _hash(key)
        idx = bisect.bisect(self._sorted, h) % len(self._sorted)  # first node clockwise
        return self._ring[self._sorted[idx]]


def _modulo_assign(key: str, servers: list[str]) -> str:
    return servers[_hash(key) % len(servers)]


def demo() -> None:
    servers = ["s1", "s2", "s3", "s4", "s5"]
    keys = [f"user:{i}" for i in range(10_000)]

    # --- Consistent hashing: removing one node should move only ~1/N keys. ---
    ring = ConsistentHashRing(vnodes=150)
    for s in servers:
        ring.add(s)
    before = {k: ring.get(k) for k in keys}
    ring.remove("s3")
    after = {k: ring.get(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])
    frac = moved / len(keys)
    # Only keys that lived on s3 (≈1/5) should move; allow generous slack.
    assert 0.10 < frac < 0.30, f"expected ~1/5 moved, got {frac:.2f}"
    # Every moved key previously belonged to the removed server.
    assert all(before[k] == "s3" for k in keys if before[k] != after[k])
    print(f"   consistent hashing: removing 1 of 5 nodes moved {frac:.1%} of keys (only s3's)")

    # --- Modulo hashing: removing one node remaps almost everything. ---
    mod_before = {k: _modulo_assign(k, servers) for k in keys}
    mod_after = {k: _modulo_assign(k, servers[:-1]) for k in keys}   # drop one server
    mod_moved = sum(1 for k in keys if mod_before[k] != mod_after[k]) / len(keys)
    assert mod_moved > 0.5, "modulo should remap the majority of keys"
    print(f"   modulo hashing:     removing 1 of 5 nodes moved {mod_moved:.1%} of keys (a stampede)")

    # --- Virtual nodes spread load reasonably evenly. ---
    from collections import Counter
    dist = Counter(after.values())
    spread = max(dist.values()) / min(dist.values())
    assert spread < 1.6, f"load should be roughly balanced, spread={spread:.2f}"
    print(f"   virtual nodes: load spread across 4 servers within {spread:.2f}x")


def main() -> None:
    print("=" * 70)
    print("SYSTEM DESIGN — consistent_hashing.py")
    print("=" * 70)
    print("A hash ring so scaling a cluster moves ~1/N keys, not all of them:")
    demo()
    print("-" * 70)
    print("Lesson: hash(key)%N reshuffles everything when N changes; a consistent-hash ring moves only ~1/N.")
    print("All consistent_hashing demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
