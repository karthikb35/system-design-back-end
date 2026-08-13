"""
01 — DSA Masterclass: Sorting & Searching
=========================================

Runnable companion to PDF Chapter "1+ — DSA Masterclass"
(sorting & binary-search sections).

  * Bubble, insertion, selection sort  -> O(n^2) family
  * Merge sort  -> stable, guaranteed O(n log n)
  * Quick sort  -> avg O(n log n), worst O(n^2)
  * Binary search  -> O(log n) on sorted data (+ bisect variants)

Each sort is verified against Python's built-in `sorted`.

Run:  python sorting_searching.py
"""

from __future__ import annotations

import bisect
import random


# ===========================================================================
# O(n^2) FAMILY
# ===========================================================================
def bubble_sort(a: list[int]) -> list[int]:
    a = a[:]
    for i in range(len(a)):
        swapped = False
        for j in range(len(a) - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:  # already sorted -> best case O(n)
            break
    return a


def insertion_sort(a: list[int]) -> list[int]:
    a = a[:]
    for i in range(1, len(a)):
        key, j = a[i], i - 1
        while j >= 0 and a[j] > key:  # shift the sorted prefix right
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a


def selection_sort(a: list[int]) -> list[int]:
    a = a[:]
    for i in range(len(a)):
        smallest = i
        for j in range(i + 1, len(a)):
            if a[j] < a[smallest]:
                smallest = j
        a[i], a[smallest] = a[smallest], a[i]  # one swap per pass -> O(n) swaps
    return a


# ===========================================================================
# O(n log n) DIVIDE & CONQUER
# ===========================================================================
def merge_sort(a: list[int]) -> list[int]:
    """Stable, guaranteed O(n log n), O(n) extra space."""
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])
    merged: list[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # <= keeps it STABLE
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(a: list[int]) -> list[int]:
    """Average O(n log n); randomized pivot avoids the O(n^2) worst case."""
    if len(a) <= 1:
        return a
    pivot = a[random.randint(0, len(a) - 1)]
    less = [x for x in a if x < pivot]
    equal = [x for x in a if x == pivot]
    greater = [x for x in a if x > pivot]
    return quick_sort(less) + equal + quick_sort(greater)


# ===========================================================================
# BINARY SEARCH — requires SORTED input, O(log n)
# ===========================================================================
def binary_search(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def first_ge(a: list[int], target: int) -> int:
    """Leftmost index with a[i] >= target — 'binary search on the boundary'."""
    return bisect.bisect_left(a, target)


def main() -> None:
    print("=" * 68)
    print("DSA MASTERCLASS — sorting_searching.py")
    print("=" * 68)

    sorts = [bubble_sort, insertion_sort, selection_sort, merge_sort, quick_sort]
    for _ in range(200):  # property test against the built-in
        data = [random.randint(-50, 50) for _ in range(random.randint(0, 30))]
        expected = sorted(data)
        for fn in sorts:
            assert fn(data) == expected, fn.__name__
    print("all 5 sorts match sorted() over 200 random cases ✔")

    arr = list(range(0, 100, 2))  # 0,2,4,...,98
    assert binary_search(arr, 42) == 21
    assert binary_search(arr, 43) == -1
    assert first_ge(arr, 43) == 22  # first index whose value >= 43 is 44 @ idx 22
    print("binary search: found 42 @ idx 21; 43 absent; first>=43 @ idx 22")

    print("-" * 68)
    print("All sorting/searching demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
