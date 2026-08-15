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


# ═══════════════════════════════════════════════════════════════════════════
# ═══  EXHAUSTIVE NOTEBOOK — sorting & searching gotchas  ═══════════════════
# ═══════════════════════════════════════════════════════════════════════════

import sys  # noqa: E402
import time  # noqa: E402


def sep(t): print(f"\n{'═'*64}\n  {t}\n{'═'*64}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §S1 — SORTING ALGORITHM GUIDE & GOTCHAS
#
# Algorithm Decision Table
# ─────────────────────────
# Bubble sort    O(n²)      Never use in production.  Pedagogical only.
# Insertion sort O(n²) avg  GOOD for small n (< ~50) or nearly-sorted data.
#                           Python's Timsort uses it for small runs.
# Selection sort O(n²)      O(n) swaps — useful when writes are expensive.
#                           NOT stable.
# Merge sort     O(n log n) Stable, guaranteed. Best for linked lists.
#                           O(n) extra space. Used in Python's Timsort.
# Quick sort     O(n log n) avg, O(n²) worst.  Best cache performance.
#                           Randomised pivot avoids worst case in practice.
# Python sorted  O(n log n) Timsort (merge + insertion). STABLE. USE THIS.
#
# GOTCHA 1: "Stable" means equal elements keep their ORIGINAL ORDER.
#   Critical when sorting objects by one key when another key already orders them.
# GOTCHA 2: Python's built-in sort is ALWAYS your first choice.
#   Custom sorts are only justified for very specific constraints (linked list,
#   external/streaming, special comparators, constant extra space).
# GOTCHA 3: Quick sort's worst case is O(n²) on SORTED OR REVERSE-SORTED input
#   with a fixed pivot. Always use a RANDOMISED pivot in production.
# GOTCHA 4: Merge sort uses O(n) extra space — relevant for large datasets.
# ──────────────────────────────────────────────────────────────────────────

def notebook_sorting_gotchas() -> None:
    sep("§S1 · Sorting Gotchas")

    # ── §S1.1  Stability matters for multi-key sorting ─────────────────────
    people = [
        ("Alice", 30), ("Bob", 25), ("Carol", 30), ("Dave", 25)
    ]
    # Sort by age first, then by name — classic multi-key stable sort
    by_age = sorted(people, key=lambda p: p[1])   # stable: Dave before Bob within age=25
    print("Stable sort by age:", by_age)
    # Bob and Dave both have age=25; they appear in original order (Alice,Bob,Carol,Dave)
    assert by_age.index(("Bob",25)) < by_age.index(("Dave",25))
    print("  Original insertion order preserved within equal keys ✓")

    # Sorting tuples: Python compares element-by-element (lexicographic)
    tasks = [("high", 3), ("low", 1), ("med", 2), ("high", 1)]
    print("\nTuple sort (first element, then second):", sorted(tasks))
    # [("high",1), ("high",3), ("low",1), ("med",2)]

    # ── §S1.2  GOTCHA: quick sort worst case on sorted input ──────────────
    import random

    def quick_sort_fixed_pivot(a):
        """DANGEROUS: always picks last element as pivot."""
        if len(a) <= 1: return a
        pivot = a[-1]   # fixed pivot = disaster on sorted input
        less    = [x for x in a[:-1] if x <= pivot]
        greater = [x for x in a[:-1] if x  > pivot]
        return quick_sort_fixed_pivot(less) + [pivot] + quick_sort_fixed_pivot(greater)

    n = 500   # small n to avoid RecursionError with the bad version
    sorted_data = list(range(n))

    t0 = time.perf_counter()
    try:
        quick_sort_fixed_pivot(sorted_data)
        t_bad = time.perf_counter() - t0
        print(f"\nFixed-pivot quicksort on sorted({n}): {t_bad*1000:.1f}ms (O(n²))")
    except RecursionError:
        print(f"\nFixed-pivot quicksort on sorted({n}): RecursionError! (stack overflow)")

    t0 = time.perf_counter()
    quick_sort(sorted_data)   # randomised pivot version
    t_good = time.perf_counter() - t0
    print(f"Random-pivot quicksort on sorted({n}): {t_good*1000:.1f}ms (O(n log n))")

    # ── §S1.3  Python's sort vs custom ────────────────────────────────────
    data = [random.randint(0, 1000) for _ in range(10_000)]

    t0 = time.perf_counter()
    sorted(data)
    t_builtin = time.perf_counter() - t0

    t0 = time.perf_counter()
    merge_sort(data)
    t_custom = time.perf_counter() - t0

    print("\nSort 10,000 random ints:")
    print(f"  Python sorted():  {t_builtin*1000:.2f}ms")
    print(f"  Custom merge_sort:{t_custom*1000:.2f}ms")
    print("  Always use Python's built-in — it's Timsort in C")

    # ── §S1.4  Key function vs cmp_to_key ─────────────────────────────────
    from functools import cmp_to_key

    # Sorting by a computed property — key is more efficient (called once per element)
    words = ["banana", "Apple", "cherry", "date", "Fig"]
    by_len_then_alpha = sorted(words, key=lambda w: (len(w), w.lower()))
    print(f"\nSort by length then alpha: {by_len_then_alpha}")

    # cmp function needed for complex comparisons (e.g., largest number from digits)
    def largest_number_cmp(a, b):
        """Compare: which ordering makes the larger concatenated number?"""
        if a + b > b + a: return -1   # a should come first
        if a + b < b + a: return 1
        return 0

    nums = ["3", "30", "34", "5", "9"]
    result = "".join(sorted(nums, key=cmp_to_key(largest_number_cmp)))
    print(f"Largest number from {nums}: {result}")   # 9534330


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §S2 — BINARY SEARCH GOTCHAS
#
# Mental model
# ────────────
# Binary search halves the search space each step: O(log n).
# REQUIRES: the input must be SORTED and support O(1) indexing.
#
# GOTCHA 1: Integer overflow in `mid = (lo + hi) // 2`.
#   (Not a Python problem — Python ints are arbitrary precision.
#    IS a problem in Java/C++: use `lo + (hi - lo) // 2` for safety.)
# GOTCHA 2: Loop condition `lo <= hi` vs `lo < hi` — different semantics!
#   lo <= hi: searches inclusive range; terminates when lo > hi.
#   lo < hi:  searches exclusive range; terminates when lo == hi.
# GOTCHA 3: Off-by-one in the return: target at `hi` when `lo <= hi` terminates.
# GOTCHA 4: bisect_left vs bisect_right — they differ on DUPLICATE elements.
#   bisect_left:  returns leftmost position where target CAN be inserted.
#   bisect_right: returns rightmost position (just after existing occurrences).
# ──────────────────────────────────────────────────────────────────────────

def notebook_binary_search_gotchas() -> None:
    sep("§S2 · Binary Search Gotchas")

    # ── §S2.1  Standard binary search ─────────────────────────────────────
    arr = list(range(0, 20, 2))   # [0,2,4,...,18]
    assert binary_search(arr, 8) == 4
    assert binary_search(arr, 7) == -1
    print("binary_search works ✓")

    # ── §S2.2  GOTCHA: bisect_left vs bisect_right on duplicates ──────────
    dup = [1, 2, 2, 2, 3, 4]
    left  = bisect.bisect_left(dup,  2)   # leftmost position of 2
    right = bisect.bisect_right(dup, 2)   # just past the last 2

    print(f"\nbisect on {dup} for target 2:")
    print(f"  bisect_left  = {left}  (index of first 2)")
    print(f"  bisect_right = {right}  (index after last 2)")
    print(f"  All 2s at indices: {list(range(left, right))}")

    # Count occurrences in O(log n)
    count = right - left
    print(f"  Occurrences of 2: {count}")

    # ── §S2.3  First/last occurrence ──────────────────────────────────────
    def first_occurrence(arr, target):
        idx = bisect.bisect_left(arr, target)
        return idx if idx < len(arr) and arr[idx] == target else -1

    def last_occurrence(arr, target):
        idx = bisect.bisect_right(arr, target) - 1
        return idx if idx >= 0 and arr[idx] == target else -1

    data = [1, 2, 2, 2, 3, 4]
    print(f"\nFirst occurrence of 2 in {data}: {first_occurrence(data, 2)}")
    print(f"Last  occurrence of 2 in {data}: {last_occurrence(data, 2)}")

    # ── §S2.4  Binary search on the ANSWER (search space != array index) ──
    #
    # Pattern: "find the minimum X such that condition(X) is True"
    # The search space is a RANGE OF VALUES, not array indices.

    def min_days_to_make_bouquets(bloomDay, m, k):
        """
        Given bloomDay[i] = day flower i blooms, find minimum days needed
        to make m bouquets each requiring k consecutive bloomed flowers.
        Binary search on the answer: day in range [min(bloomDay), max(bloomDay)].
        """
        if m * k > len(bloomDay): return -1

        def can_make(day):
            bouquets = consecutive = 0
            for d in bloomDay:
                if d <= day:
                    consecutive += 1
                    if consecutive == k:
                        bouquets += 1; consecutive = 0
                else:
                    consecutive = 0
            return bouquets >= m

        lo, hi = min(bloomDay), max(bloomDay)
        while lo < hi:
            mid = (lo + hi) // 2
            if can_make(mid): hi = mid    # mid works, try earlier
            else:             lo = mid + 1  # too early, need more days
        return lo

    result = min_days_to_make_bouquets([1,10,3,10,2], m=3, k=1)
    print(f"\nBinary search on answer: min days for bouquets = {result}")   # 3


def run_sorting_notebook() -> None:
    notebook_sorting_gotchas()
    notebook_binary_search_gotchas()
    print("\n" + "═"*64)
    print("  SORTING & SEARCHING NOTEBOOK COMPLETE")
    print("═"*64)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
    run_sorting_notebook()

