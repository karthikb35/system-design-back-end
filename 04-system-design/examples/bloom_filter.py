"""
04 — System Design: Bloom Filter (probabilistic membership at scale)
====================================================================

Runnable companion to PDF Book V "Answering 'have I seen this before?' cheaply".

A Bloom filter is a compact, probabilistic set. It answers "is X in the set?"
using a bit array and k hash functions. Its defining trade-off:

    * "NO"  is always correct   (no false negatives)
    * "YES" might be wrong      (a bounded false-positive rate)

In exchange it uses a fraction of the memory a real set would, and never stores
the elements themselves. Used to skip disk/DB/network lookups for keys that are
definitely absent: Cassandra/HBase SSTables, CDNs, "have we emailed this user?",
malicious-URL checks.

This file builds one from scratch and verifies: zero false negatives, and a
false-positive rate close to the theoretical prediction.
"""

from __future__ import annotations

import hashlib
import math


class BloomFilter:
    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        # Optimal bit-array size m and hash count k from the standard formulas.
        self._m = self._optimal_m(expected_items, false_positive_rate)
        self._k = self._optimal_k(self._m, expected_items)
        self._bits = bytearray((self._m + 7) // 8)
        self._n = 0

    @staticmethod
    def _optimal_m(n: int, p: float) -> int:
        return max(8, int(-(n * math.log(p)) / (math.log(2) ** 2)))

    @staticmethod
    def _optimal_k(m: int, n: int) -> int:
        return max(1, round((m / n) * math.log(2)))

    def _indexes(self, item: str):
        # Double hashing: derive k indexes from two base hashes (Kirsch-Mitzenmacher).
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)
        for i in range(self._k):
            yield (h1 + i * h2) % self._m

    def add(self, item: str) -> None:
        for idx in self._indexes(item):
            self._bits[idx // 8] |= (1 << (idx % 8))
        self._n += 1

    def __contains__(self, item: str) -> bool:
        return all(self._bits[idx // 8] & (1 << (idx % 8)) for idx in self._indexes(item))


def demo() -> None:
    bf = BloomFilter(expected_items=10_000, false_positive_rate=0.01)
    present = [f"user:{i}" for i in range(10_000)]
    for item in present:
        bf.add(item)

    # No false negatives — everything added must report present.
    assert all(item in bf for item in present), "Bloom filters never have false negatives"
    print(f"   {len(present)} items added; zero false negatives (guaranteed)")

    # Measure the false-positive rate on 10k keys we never inserted.
    absent = [f"ghost:{i}" for i in range(10_000)]
    false_positives = sum(1 for item in absent if item in bf)
    fp_rate = false_positives / len(absent)
    assert fp_rate < 0.05, f"false-positive rate should be near 1%, got {fp_rate:.3f}"
    print(f"   false-positive rate on unseen keys: {fp_rate:.2%} (target ~1%)")

    # Memory: bits, not objects. Report the compression vs storing the strings.
    bloom_bytes = len(bf._bits)
    naive_bytes = sum(len(s) for s in present)   # rough lower bound for a real set
    print(f"   memory: {bloom_bytes:,} bytes vs ~{naive_bytes:,} bytes to store the keys "
          f"({naive_bytes / bloom_bytes:.0f}x smaller)")


def main() -> None:
    print("=" * 70)
    print("SYSTEM DESIGN — bloom_filter.py")
    print("=" * 70)
    print("A probabilistic set: 'no' is certain, 'yes' is probable, memory is tiny:")
    demo()
    print("-" * 70)
    print("Lesson: use a Bloom filter to cheaply skip lookups for keys that are DEFINITELY absent (no false negatives).")
    print("All bloom_filter demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
