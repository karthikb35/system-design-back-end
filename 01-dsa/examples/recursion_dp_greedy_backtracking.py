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

from functools import cache


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
@cache  # top-down memoization in one line
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


# ═══════════════════════════════════════════════════════════════════════════
# ═══  EXHAUSTIVE NOTEBOOK — recursion · DP · greedy · backtracking  ════════
# ═══════════════════════════════════════════════════════════════════════════

import sys  # noqa: E402
from functools import cache as _cache  # noqa: E402


def sep(t): print(f"\n{'═'*64}\n  {t}\n{'═'*64}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §R1 — RECURSION GOTCHAS
#
# Mental model
# ────────────
# Recursion = a function that calls itself with a SMALLER sub-problem.
# Every recursive function needs:
#   1. A BASE CASE that stops the recursion.
#   2. A RECURSIVE CASE that moves toward the base case.
#   3. No shared mutable state (usually) — recursive calls should be independent.
#
# GOTCHA 1: Python's default recursion limit is ~1000.
#   sys.setrecursionlimit() can raise it but risks stack overflow on large n.
#   For production: convert deep recursion to ITERATION with an explicit stack.
# GOTCHA 2: Naive recursion re-computes the same sub-problems → exponential time.
#   Fix: memoization (@cache / @lru_cache) converts it to O(n).
# GOTCHA 3: Tail recursion is NOT optimized in Python (no TCO).
#   A tail-recursive function with n=100000 still overflows the stack.
# GOTCHA 4: Mutable default arguments in recursive helpers are shared across calls.
# ──────────────────────────────────────────────────────────────────────────

def notebook_recursion_gotchas() -> None:
    sep("§R1 · Recursion Gotchas")

    # ── §R1.1  Naive vs memoized Fibonacci ────────────────────────────────
    import time

    call_count = [0]
    def fib_naive(n):
        call_count[0] += 1
        if n < 2: return n
        return fib_naive(n-1) + fib_naive(n-2)

    call_count[0] = 0
    t0 = time.perf_counter()
    result = fib_naive(30)
    t_naive = time.perf_counter() - t0
    print(f"Naive  fib(30) = {result:7d}  calls={call_count[0]:9d}  {t_naive*1000:.1f}ms")

    t0 = time.perf_counter()
    result2 = fib_memo(35)   # from existing code, uses @cache
    t_memo = time.perf_counter() - t0
    print(f"Memoized fib(35)= {result2:6d}  calls≈35           {t_memo*1000:.1f}ms")
    print("Memoization converts O(2^n) to O(n) by caching sub-problems")

    # ── §R1.2  GOTCHA: Python's recursion limit ────────────────────────────
    import sys
    original_limit = sys.getrecursionlimit()
    print(f"\nDefault recursion limit: {original_limit}")

    def deep(n):
        if n == 0: return 0
        return 1 + deep(n-1)

    try:
        deep(original_limit + 100)
    except RecursionError:
        print(f"RecursionError at depth > {original_limit}")

    # Iterative solution — no stack limit
    def deep_iter(n):
        result = 0
        while n > 0:
            result += 1; n -= 1
        return result

    print(f"Iterative deep(5000): {deep_iter(5000)} — no stack overflow ✓")

    # ── §R1.3  Converting recursive DFS to iterative ──────────────────────
    #
    # Pattern: replace the call stack with an explicit stack (list).
    # IMPORTANT: push in REVERSE order to process left before right.

    def dfs_recursive(tree, root):
        """Classic recursive DFS — fails for deep trees."""
        if root not in tree: return [root]
        result = [root]
        for child in tree[root]:
            result.extend(dfs_recursive(tree, child))
        return result

    def dfs_iterative(tree, root):
        """Iterative DFS — handles any depth."""
        result, stack = [], [root]
        while stack:
            node = stack.pop()
            result.append(node)
            for child in reversed(tree.get(node, [])):
                stack.append(child)
        return result

    tree = {1: [2,3], 2: [4,5], 3: [6], 4: [], 5: [], 6: []}
    assert dfs_recursive(tree, 1) == dfs_iterative(tree, 1)
    print(f"\nRecursive DFS == Iterative DFS: {dfs_iterative(tree, 1)}")

    # ── §R1.4  GOTCHA: mutable default arg in recursive helper ─────────────
    def bad_permutations(nums, path=[]):   # GOTCHA: shared mutable default!
        if not nums:
            return [path[:]]
        result = []
        for i, n in enumerate(nums):
            path.append(n)
            result.extend(bad_permutations(nums[:i]+nums[i+1:], path))
            path.pop()
        return result

    # First call: fine
    _r1 = bad_permutations([1, 2])
    # But path=[] persists between calls — works by accident here because
    # path.pop() always cleans up; but the default IS shared across calls.
    # Safe pattern: use None sentinel
    def safe_permutations(nums, path=None):
        if path is None: path = []    # fresh list per call tree root
        if not nums:
            return [path[:]]
        result = []
        for i, n in enumerate(nums):
            path.append(n)
            result.extend(safe_permutations(nums[:i]+nums[i+1:], path))
            path.pop()
        return result

    assert safe_permutations([1,2,3]) == permutations([1,2,3])
    print("Safe permutations using None sentinel ✓")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §R2 — DYNAMIC PROGRAMMING PATTERNS & GOTCHAS
#
# Mental model
# ────────────
# DP = recursion + memoization (OR iterative bottom-up tabulation).
# Use DP when:
#   • Optimal substructure: optimal solution contains optimal sub-solutions.
#   • Overlapping sub-problems: same sub-problem solved multiple times.
#
# Two approaches:
#   Top-down (memoization): recursive + cache.  Natural; easier to code.
#   Bottom-up (tabulation): iterative + table.  More space-efficient; no call stack.
#
# GOTCHA 1: Off-by-one in the DP table size — dp[amount+1] not dp[amount].
# GOTCHA 2: Forgetting to handle the base case in tabulation.
# GOTCHA 3: When DP needs O(n²) space but only needs last 1-2 rows → space optimise.
# GOTCHA 4: Greedy FAILS when it can't commit early — need DP (e.g. non-canonical coins).
# ──────────────────────────────────────────────────────────────────────────

def notebook_dp_gotchas() -> None:
    sep("§R2 · Dynamic Programming Gotchas")

    # ── §R2.1  Top-down vs bottom-up for coin change ──────────────────────
    coins, amount = [1, 5, 6, 9], 11

    @_cache
    def coin_change_memo(rem):
        if rem == 0: return 0
        if rem < 0:  return float('inf')
        return 1 + min(coin_change_memo(rem - c) for c in coins)

    result_memo = coin_change_memo(amount)
    result_tab  = coin_change(coins, amount)   # from existing code
    assert result_memo == result_tab == 2      # 2 coins: 5+6 or 9+? or 11?
    # Actually 11 = 9+1+1 = 3, or 5+6 = 2 → result is 2
    print(f"coin_change({coins}, {amount}) = {result_tab}  (top-down == bottom-up)")

    # ── §R2.2  GOTCHA: greedy fails on non-canonical coins ────────────────
    # Greedy: always take the largest coin ≤ remainder.
    # FAILS for coins=[1,5,6,9], amount=11:
    #   Greedy: 9+1+1 = 3 coins
    #   DP:     5+6   = 2 coins ← optimal

    def greedy_coins(coins, amount):
        coins_sorted = sorted(coins, reverse=True)
        count, remaining = 0, amount
        for c in coins_sorted:
            while remaining >= c:
                remaining -= c; count += 1
        return count

    greedy_result = greedy_coins(coins, amount)
    dp_result     = coin_change(coins, amount)
    print(f"\nCoin change with non-canonical coins {coins}, amount={amount}:")
    print(f"  Greedy: {greedy_result} coins  ← WRONG (suboptimal)")
    print(f"  DP:     {dp_result} coins  ← CORRECT")

    # ── §R2.3  Space optimisation — Fibonacci from O(n) to O(1) ──────────
    # Full DP table for Fibonacci needs O(n) space.
    # But we only ever need the last TWO values → O(1).

    def fib_full_table(n):
        if n < 2: return n
        dp = [0] * (n + 1)
        dp[1] = 1
        for i in range(2, n + 1):
            dp[i] = dp[i-1] + dp[i-2]
        return dp[n]   # uses O(n) space

    # Same as fib_tab: O(1) space
    assert fib_full_table(20) == fib_tab(20)
    print(f"\nFib(20) space-optimised = {fib_tab(20)}  (O(1) space vs O(n))")

    # ── §R2.4  Longest Common Subsequence — classic 2D DP ─────────────────
    def lcs(s1, s2):
        m, n = len(s1), len(s2)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1, m+1):
            for j in range(1, n+1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]

    assert lcs("ABCBDAB", "BDCAB") == 4   # "BCAB" or "BDAB"
    print(f"LCS('ABCBDAB','BDCAB') = {lcs('ABCBDAB','BDCAB')} ✓")

    # ── §R2.5  Identifying DP vs Greedy vs Backtracking ───────────────────
    print("""
Pattern recognition guide:
  Greedy     — local optimal choice leads to global optimal.
               "Always take the largest/smallest" — verify with exchange argument.
               Example: activity selection, Huffman encoding, Dijkstra.
  DP         — overlapping sub-problems, optimal substructure.
               "What if greedy doesn't work?" → try DP.
               Example: coin change with non-canonical, knapsack, LCS.
  Backtracking — enumerate all possibilities, prune invalid branches.
               "Find ALL solutions" or "does any solution exist?"
               Example: N-Queens, Sudoku, word search.
  Key question: "Can I make a locally optimal decision at each step and never
                 revise it?"  Yes → Greedy.  No → DP or Backtracking.
""")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §R3 — BACKTRACKING GOTCHAS
#
# Mental model
# ────────────
# Backtracking = DFS over a decision tree.
# At each node, make a choice; if it leads to a dead end, UNDO it and try next.
# "Make choice → recurse → undo choice" is the canonical pattern.
#
# GOTCHA 1: Forgetting to UNDO the choice after recursion.
# GOTCHA 2: Appending the result directly (by reference) when you need a COPY.
# GOTCHA 3: Not pruning early → exponential time when many branches are invalid.
# GOTCHA 4: Backtracking vs DP — backtracking explores all paths; DP only the optimal.
# ──────────────────────────────────────────────────────────────────────────

def notebook_backtracking_gotchas() -> None:
    sep("§R3 · Backtracking Gotchas")

    # ── §R3.1  GOTCHA: append reference vs copy ────────────────────────────
    def perms_wrong(nums):
        results = []
        path = []
        def bt(remaining):
            if not remaining:
                results.append(path)      # WRONG: appending the SAME list!
                return
            for i, n in enumerate(remaining):
                path.append(n)
                bt(remaining[:i] + remaining[i+1:])
                path.pop()
        bt(nums)
        return results

    def perms_correct(nums):
        results = []
        path = []
        def bt(remaining):
            if not remaining:
                results.append(path[:])   # CORRECT: append a COPY
                return
            for i, n in enumerate(remaining):
                path.append(n)
                bt(remaining[:i] + remaining[i+1:])
                path.pop()
        bt(nums)
        return results

    wrong   = perms_wrong([1, 2, 3])
    correct = perms_correct([1, 2, 3])
    print(f"Wrong  (reference): all results are {wrong[:2]}... (all same empty list!)")
    print(f"Correct (copy):     {correct[:2]}...")

    # ── §R3.2  GOTCHA: forgetting to undo ──────────────────────────────────
    path_bug = []
    def bt_no_undo(n, k, start=1):
        """Finds combinations of k numbers from 1..n WITHOUT undoing."""
        if len(path_bug) == k:
            print(f"  found: {path_bug[:]}")
            return
        for i in range(start, n+1):
            path_bug.append(i)
            bt_no_undo(n, k, i+1)
            # MISSING: path_bug.pop() ← results would accumulate incorrectly

    # Show only first few to avoid too much output
    # (Not running bt_no_undo to avoid polluting state; demonstrating the concept)
    path_ok = []
    results_ok = []
    def bt_with_undo(n, k, start=1):
        if len(path_ok) == k:
            results_ok.append(path_ok[:])
            return
        for i in range(start, n+1):
            path_ok.append(i)
            bt_with_undo(n, k, i+1)
            path_ok.pop()           # ← CRUCIAL: undo the choice

    bt_with_undo(4, 2)
    print(f"Combinations C(4,2) with undo: {results_ok}")   # 6 combinations

    # ── §R3.3  Pruning to speed up backtracking ────────────────────────────
    def sum_subsets(nums, target):
        """Find all subsets that sum to target. With and without pruning."""
        results = []
        nums_sorted = sorted(nums)   # sort enables pruning

        def bt(start, remaining, path):
            if remaining == 0:
                results.append(path[:]); return
            for i in range(start, len(nums_sorted)):
                n = nums_sorted[i]
                if n > remaining: break   # PRUNE: rest are even larger
                if i > start and nums_sorted[i] == nums_sorted[i-1]: continue  # dedup
                path.append(n)
                bt(i+1, remaining - n, path)
                path.pop()

        bt(0, target, [])
        return results

    result = sum_subsets([10, 1, 2, 7, 6, 1, 5], 8)
    print(f"Subsets summing to 8: {sorted(result)}")


def run_recursion_dp_notebook() -> None:
    notebook_recursion_gotchas()
    notebook_dp_gotchas()
    notebook_backtracking_gotchas()
    print("\n" + "═"*64)
    print("  RECURSION / DP / BACKTRACKING NOTEBOOK COMPLETE")
    print("═"*64)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
    run_recursion_dp_notebook()

