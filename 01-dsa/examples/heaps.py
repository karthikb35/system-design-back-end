"""
01 — DSA Internals: Binary Heap From Scratch (Priority Queue & Heapsort)
=======================================================================

Runnable companion to PDF Book II "How heapq / a priority queue works".

A binary heap is a COMPLETE binary tree stored in a flat array — no pointers.
For a node at index i:
    parent(i) = (i - 1) // 2
    left(i)   = 2*i + 1
    right(i)  = 2*i + 2

A MIN-heap keeps the smallest element at the root. Two O(log n) operations:
    sift_up   — after push, bubble the new leaf up while smaller than its parent
    sift_down — after pop, move the last element to the root and sink it

This file builds the heap, uses it as a priority queue, and derives HEAPSORT
(build heap + repeatedly pop the min) — an in-place O(n log n) sort.
"""

from __future__ import annotations


class MinHeap:
    def __init__(self):
        self._a: list = []

    def __len__(self) -> int:
        return len(self._a)

    def peek(self):
        if not self._a:
            raise IndexError("peek from empty heap")
        return self._a[0]

    def push(self, x) -> None:
        self._a.append(x)
        self._sift_up(len(self._a) - 1)

    def pop(self):
        if not self._a:
            raise IndexError("pop from empty heap")
        top = self._a[0]
        last = self._a.pop()
        if self._a:
            self._a[0] = last               # move last leaf to root
            self._sift_down(0)              # sink it to its place
        return top

    def _sift_up(self, i: int) -> None:
        a = self._a
        while i > 0:
            parent = (i - 1) // 2
            if a[i] < a[parent]:
                a[i], a[parent] = a[parent], a[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        a = self._a
        n = len(a)
        while True:
            smallest = i
            left, right = 2 * i + 1, 2 * i + 2
            if left < n and a[left] < a[smallest]:
                smallest = left
            if right < n and a[right] < a[smallest]:
                smallest = right
            if smallest == i:
                break
            a[i], a[smallest] = a[smallest], a[i]
            i = smallest

    @classmethod
    def heapify(cls, items) -> "MinHeap":
        """Build a heap from an arbitrary list in O(n) — bottom-up, NOT n pushes."""
        h = cls()
        h._a = list(items)
        for i in range(len(h._a) // 2 - 1, -1, -1):
            h._sift_down(i)
        return h


def heapsort(data: list) -> list:
    """O(n log n) sort: heapify once, then pop the min n times."""
    h = MinHeap.heapify(data)
    return [h.pop() for _ in range(len(h))]


def demo() -> None:
    import random

    # Priority queue behaviour: pops always come out in sorted order.
    h = MinHeap()
    values = [5, 3, 8, 1, 9, 2, 7, 4, 6, 0]
    for v in values:
        h.push(v)
    assert h.peek() == 0
    popped = [h.pop() for _ in range(len(values))]
    assert popped == sorted(values), "min-heap must pop ascending"
    print(f"   pushed {values}")
    print(f"   popped {popped}  (always ascending — that's the priority queue)")

    # O(n) heapify then heapsort matches Python's sorted().
    data = [random.randint(0, 1000) for _ in range(500)]
    assert heapsort(data) == sorted(data)
    print("   heapsort(500 random ints) matches sorted()  — O(n log n), in-place heap")

    # heapify is O(n), not n * O(log n).
    big = list(range(10_000, 0, -1))
    hh = MinHeap.heapify(big)
    assert hh.peek() == 1
    print("   heapify(10k reversed) builds a valid heap in one O(n) pass")


def main() -> None:
    print("=" * 70)
    print("DSA INTERNALS — heaps.py (binary min-heap)")
    print("=" * 70)
    print("Array-backed complete tree; sift_up / sift_down are O(log n):")
    demo()
    print("-" * 70)
    print("Lesson: a heap = O(1) peek-min, O(log n) push/pop; heapify is O(n). Basis of heapq & Dijkstra.")
    print("All heaps demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
