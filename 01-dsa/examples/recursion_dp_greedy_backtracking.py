"""
01 — DSA Masterclass: Recursion, Dynamic Programming, Greedy, Backtracking
==========================================================================

Runnable companion to PDF Chapter "1+ — DSA Masterclass"
(recursion / DP / greedy / backtracking sections).

  * Recursion         — factorial, Fibonacci, Tower of Hanoi
  * Dynamic Programming — memoized & tabulated fib, climbing stairs,
                          coin change (min coins), 0/1 knapsack, LCS
  * Greedy            — activity selection, canonical coin change
  * Backtracking      — permutations, subsets, N-Queens

Run:  python recursion_dp_greedy_backtracking.py
"""

from __future__ import annotations

from functools import lru_cache


# ===========================================================================
# RECURSION
# ===========================================================================
def factorial(n: int) -> int:
    if n <= 1:               # base case
        return 1
    return n * factorial(n - 1)


def hanoi(n: int, src: str, aux: str, dst: str) -> list[tuple[str, str]]:
    if n == 0:
        return []
    return (
        hanoi(n - 1, src, dst, aux)
        + [(src, dst)]
        + hanoi(n - 1, aux, src, dst)
    )


# ===========================================================================
# DYNAMIC PROGRAMMING
# ===========================================================================
@lru_cache(maxsize=None)  # top-down memoization in one line
def fib_memo(n: int) -> int:
    if n < 2:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)


def fib_tab(n: int) -> int:  # bottom-up tabulation, O(1) space
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def climbing_stairs(n: int) -> int:
    """Ways to reach step n taking 1 or 2 steps — same shape as Fibonacci."""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def coin_change(coins: list[int], amount: int) -> int:
    """Fewest coins to make `amount`, or -1. Bottom-up DP, O(amount * coins)."""
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] != INF else -1


def knapsack_01(weights: list[int], values: list[int], cap: int) -> int:
    """Max value with a weight budget — classic 0/1 knapsack DP."""
    dp = [0] * (cap + 1)
    for w, v in zip(weights, values):
        for c in range(cap, w - 1, -1):  # reverse -> each item used at most once
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[cap]


def longest_common_subseq(x: str, y: str) -> int:
    dp = [[0] * (len(y) + 1) for _ in range(len(x) + 1)]
    for i in range(1, len(x) + 1):
        for j in range(1, len(y) + 1):
            if x[i - 1] == y[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[len(x)][len(y)]


# ===========================================================================
# GREEDY
# ===========================================================================
def activity_selection(intervals: list[tuple[int, int]]) -> int:
    """Max non-overlapping intervals — pick earliest finish time (greedy)."""
    count, end = 0, float("-inf")
    for start, finish in sorted(intervals, key=lambda iv: iv[1]):
        if start >= end:
            count += 1
            end = finish
    return count


def greedy_change(amount: int, coins: tuple[int, ...] = (25, 10, 5, 1)) -> list[int]:
    """Greedy works for CANONICAL coin systems (e.g. US coins)."""
    out: list[int] = []
    for coin in coins:  # largest first
        while amount >= coin:
            amount -= coin
            out.append(coin)
    return out


# ===========================================================================
# BACKTRACKING — choose / explore / un-choose
# ===========================================================================
def permutations(nums: list[int]) -> list[list[int]]:
    result: list[list[int]] = []

    def backtrack(path: list[int], remaining: list[int]) -> None:
        if not remaining:
            result.append(path[:])
            return
        for i in range(len(remaining)):
            path.append(remaining[i])
            backtrack(path, remaining[:i] + remaining[i + 1:])
            path.pop()  # un-choose

    backtrack([], nums)
    return result


def subsets(nums: list[int]) -> list[list[int]]:
    result: list[list[int]] = []

    def backtrack(start: int, path: list[int]) -> None:
        result.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return result


def solve_n_queens(n: int) -> int:
    """Count valid placements — pruned DFS over columns."""
    cols: set[int] = set()
    diag1: set[int] = set()  # row - col
    diag2: set[int] = set()  # row + col
    count = 0

    def place(row: int) -> None:
        nonlocal count
        if row == n:
            count += 1
            return
        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue  # prune: attacked
            cols.add(col); diag1.add(row - col); diag2.add(row + col)
            place(row + 1)
            cols.discard(col); diag1.discard(row - col); diag2.discard(row + col)

    place(0)
    return count


def main() -> None:
    print("=" * 68)
    print("DSA MASTERCLASS — recursion_dp_greedy_backtracking.py")
    print("=" * 68)

    assert factorial(5) == 120
    assert len(hanoi(3, "A", "B", "C")) == 7  # 2^n - 1 moves
    print("recursion: 5! = 120; Hanoi(3) = 7 moves")

    assert fib_memo(30) == 832040 == fib_tab(30)
    assert climbing_stairs(5) == 8
    assert coin_change([1, 3, 4], 6) == 2      # 3+3 (greedy would fail here)
    assert knapsack_01([1, 3, 4, 5], [1, 4, 5, 7], 7) == 9
    assert longest_common_subseq("ABCBDAB", "BDCAB") == 4
    print("DP: fib(30)=832040, stairs(5)=8, coin_change=2, knapsack=9, LCS=4")

    assert activity_selection([(1, 4), (3, 5), (0, 6), (5, 7), (3, 9),
                               (5, 9), (6, 10), (8, 11), (8, 12),
                               (2, 14), (12, 16)]) == 4
    assert greedy_change(41) == [25, 10, 5, 1]
    print("greedy: activities=4; change(41) ->", greedy_change(41))

    assert len(permutations([1, 2, 3])) == 6
    assert len(subsets([1, 2, 3])) == 8       # 2^n
    assert solve_n_queens(8) == 92            # famous answer
    print("backtracking: perms(3)=6, subsets(3)=8, 8-queens=92 solutions")

    print("-" * 68)
    print("All recursion/DP/greedy/backtracking demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
