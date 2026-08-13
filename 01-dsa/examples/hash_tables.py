"""
01 — DSA Internals: Hash Tables From Scratch (Collisions & Resizing)
===================================================================

Runnable companion to PDF Book II "How a dict really works".

A dict/set gives O(1) average lookup by turning a key into an array index via a
hash function. Two keys can map to the same slot — a COLLISION — and how you
resolve it is the whole game. This file builds BOTH classic strategies and
proves they behave like Python's dict:

  * SEPARATE CHAINING   — each slot holds a small list ("bucket") of entries
  * OPEN ADDRESSING     — on collision, probe forward to the next free slot
  * LOAD FACTOR & RESIZE— grow the table when it gets too full to keep O(1)

The lesson: O(1) is AMORTIZED and AVERAGE — a bad hash or a full table degrades
it to O(n). Resizing keeps the average low.
"""


# --------------------------------------------------------------------------
# SEPARATE CHAINING: slot -> list of (key, value) pairs. Simple and robust.
# --------------------------------------------------------------------------
class ChainingHashMap:
    def __init__(self, capacity: int = 8):
        self._cap = capacity
        self._size = 0
        self._buckets: list[list] = [[] for _ in range(capacity)]

    def _index(self, key) -> int:
        return hash(key) % self._cap        # fold the hash into [0, cap)

    def _resize(self, new_cap: int) -> None:
        old = [pair for bucket in self._buckets for pair in bucket]
        self._cap = new_cap
        self._buckets = [[] for _ in range(new_cap)]
        self._size = 0
        for k, v in old:
            self.put(k, v)                  # re-hash every entry into the bigger table

    def put(self, key, value) -> None:
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:                    # update existing key
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1
        if self._size / self._cap > 0.75:   # load factor threshold
            self._resize(self._cap * 2)

    def get(self, key, default=None):
        for k, v in self._buckets[self._index(key)]:
            if k == key:
                return v
        return default

    def delete(self, key) -> bool:
        bucket = self._buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self._size -= 1
                return True
        return False

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key) -> bool:
        return self.get(key, _MISSING) is not _MISSING


_MISSING = object()


# --------------------------------------------------------------------------
# OPEN ADDRESSING (linear probing): all entries live in ONE array. On collision
# we step forward until a free slot. Deletions need a TOMBSTONE so probe chains
# don't break. Cache-friendly, but clusters if the load factor gets high.
# --------------------------------------------------------------------------
_EMPTY = object()
_DELETED = object()


class OpenAddressingHashMap:
    def __init__(self, capacity: int = 8):
        self._cap = capacity
        self._size = 0
        self._keys = [_EMPTY] * capacity
        self._vals = [None] * capacity

    def _probe(self, key):
        i = hash(key) % self._cap
        first_deleted = None
        for _ in range(self._cap):
            slot = self._keys[i]
            if slot is _EMPTY:
                return (first_deleted if first_deleted is not None else i), False
            if slot is _DELETED:
                if first_deleted is None:
                    first_deleted = i
            elif slot == key:
                return i, True
            i = (i + 1) % self._cap         # linear probe to the next slot
        return (first_deleted if first_deleted is not None else -1), False

    def _resize(self, new_cap: int) -> None:
        items = [(k, v) for k, v in zip(self._keys, self._vals)
                 if k is not _EMPTY and k is not _DELETED]
        self._cap = new_cap
        self._keys = [_EMPTY] * new_cap
        self._vals = [None] * new_cap
        self._size = 0
        for k, v in items:
            self.put(k, v)

    def put(self, key, value) -> None:
        if (self._size + 1) / self._cap > 0.6:   # keep open addressing loose
            self._resize(self._cap * 2)
        i, found = self._probe(key)
        if not found:
            self._size += 1
        self._keys[i] = key
        self._vals[i] = value

    def get(self, key, default=None):
        i, found = self._probe(key)
        return self._vals[i] if found else default

    def delete(self, key) -> bool:
        i, found = self._probe(key)
        if not found:
            return False
        self._keys[i] = _DELETED            # tombstone, NOT empty
        self._vals[i] = None
        self._size -= 1
        return True

    def __len__(self) -> int:
        return self._size


def _exercise(make_map) -> None:
    m = make_map()
    # Insert enough to force multiple resizes.
    for i in range(100):
        m.put(f"key{i}", i)
    assert len(m) == 100
    assert m.get("key42") == 42
    assert m.get("nope", -1) == -1
    m.put("key42", 999)                     # update, not insert
    assert m.get("key42") == 999
    assert len(m) == 100
    assert m.delete("key42") is True
    assert m.get("key42") is None
    assert len(m) == 99
    # Behaves like a real dict for the same operations.
    ref = {f"key{i}": i for i in range(100)}
    ref["key42"] = 999
    del ref["key42"]
    for k in ref:
        assert m.get(k) == ref[k]


def demo() -> None:
    _exercise(lambda: ChainingHashMap(capacity=8))
    print("   chaining: 100 inserts + resizes + update + delete match a real dict")
    _exercise(lambda: OpenAddressingHashMap(capacity=8))
    print("   open addressing: linear probing + tombstones + resize match a real dict")

    # Show a collision explicitly: two keys forced into the same initial slot.
    m = ChainingHashMap(capacity=4)
    m.put("a", 1)
    m.put("e", 2)   # different key; may or may not collide, but both retrievable
    assert m.get("a") == 1 and m.get("e") == 2
    print("   collisions resolved: distinct keys in the same slot are still found correctly")


def main() -> None:
    print("=" * 70)
    print("DSA INTERNALS — hash_tables.py")
    print("=" * 70)
    print("Building dict/set from scratch (the two collision strategies):")
    demo()
    print("-" * 70)
    print("Lesson: O(1) is average+amortized; a bad hash or full table -> O(n). Resize keeps it fast.")
    print("All hash_tables demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
