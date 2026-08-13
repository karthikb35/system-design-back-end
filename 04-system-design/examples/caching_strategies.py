"""
04 — System Design: Caching Strategies & Eviction Policies
==========================================================

Runnable companion to PDF Book V "Caching: the first lever for read scale".

A cache trades memory for latency by keeping hot data close. The design choices:

  EVICTION (what to drop when full):
    * LRU — Least Recently Used   (drop the coldest-by-time)
    * LFU — Least Frequently Used (drop the coldest-by-count)

  WRITE POLICY (how writes reach the store):
    * cache-aside   — app reads cache, on miss loads DB and fills cache
    * write-through — write cache AND DB together (consistent, slower writes)
    * write-back    — write cache now, flush to DB later (fast, risk on crash)

This file builds an O(1) LRU cache and an LFU cache from scratch and models the
cache-aside read path, asserting hits, misses, and eviction order.
"""

from __future__ import annotations
from collections import OrderedDict, Counter, defaultdict


class LRUCache:
    """O(1) get/put via an ordered dict; most-recent at the end."""
    def __init__(self, capacity: int):
        self._cap = capacity
        self._data: "OrderedDict[str, object]" = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key not in self._data:
            self.misses += 1
            return None
        self._data.move_to_end(key)        # mark as most-recently used
        self.hits += 1
        return self._data[key]

    def put(self, key, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._cap:
            self._data.popitem(last=False)  # evict least-recently used (front)


class LFUCache:
    """Evict the least-frequently used; ties broken by oldest."""
    def __init__(self, capacity: int):
        self._cap = capacity
        self._val: dict = {}
        self._freq: Counter = Counter()
        self._order: dict = {}             # key -> insertion tiebreak
        self._seq = 0

    def get(self, key):
        if key not in self._val:
            return None
        self._freq[key] += 1
        return self._val[key]

    def put(self, key, value) -> None:
        if self._cap == 0:
            return
        if key not in self._val and len(self._val) >= self._cap:
            # Evict min frequency, then oldest among ties.
            victim = min(self._val, key=lambda k: (self._freq[k], self._order[k]))
            del self._val[victim]; del self._freq[victim]; del self._order[victim]
        self._val[key] = value
        self._freq[key] += 1
        self._order[key] = self._seq
        self._seq += 1


class CacheAside:
    """The most common pattern: app checks cache, loads DB on miss, fills cache."""
    def __init__(self, db: dict, capacity: int = 2):
        self._db = db
        self._cache = LRUCache(capacity)
        self.db_reads = 0

    def read(self, key):
        value = self._cache.get(key)
        if value is not None:              # cache hit
            return value
        self.db_reads += 1                 # cache miss -> hit the DB
        value = self._db.get(key)
        if value is not None:
            self._cache.put(key, value)    # populate for next time
        return value


def demo() -> None:
    # LRU eviction order.
    lru = LRUCache(capacity=2)
    lru.put("a", 1); lru.put("b", 2)
    assert lru.get("a") == 1               # 'a' now most-recent
    lru.put("c", 3)                        # capacity exceeded -> evict 'b' (LRU)
    assert lru.get("b") is None and lru.get("a") == 1 and lru.get("c") == 3
    print(f"   LRU: evicted the least-recently-used key; hits={lru.hits} misses={lru.misses}")

    # LFU keeps the frequently-used key even if it's older.
    lfu = LFUCache(capacity=2)
    lfu.put("x", 1); lfu.put("y", 2)
    lfu.get("x"); lfu.get("x"); lfu.get("y")   # x used 3x (incl put), y 2x
    lfu.put("z", 3)                            # evict least-frequent -> 'y'
    assert lfu.get("y") is None and lfu.get("x") == 1 and lfu.get("z") == 3
    print("   LFU: kept the frequently-used key, evicted the rarely-used one")

    # Cache-aside: second read of the same key is served from cache (no DB hit).
    db = {"user:1": "Ada", "user:2": "Linus", "user:3": "Grace"}
    ca = CacheAside(db, capacity=2)
    assert ca.read("user:1") == "Ada" and ca.db_reads == 1   # miss -> DB
    assert ca.read("user:1") == "Ada" and ca.db_reads == 1   # hit -> no DB read
    ca.read("user:2"); ca.read("user:3")                     # evicts user:1
    assert ca.read("user:1") == "Ada" and ca.db_reads == 4   # evicted -> DB again
    print(f"   cache-aside: {ca.db_reads} DB reads for 5 requests (cache absorbed the rest)")


def main() -> None:
    print("=" * 70)
    print("SYSTEM DESIGN — caching_strategies.py")
    print("=" * 70)
    print("Eviction (LRU/LFU) and the cache-aside read path, from scratch:")
    demo()
    print("-" * 70)
    print("Lesson: caching trades memory for latency; the hard parts are eviction policy and invalidation.")
    print("All caching_strategies demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
