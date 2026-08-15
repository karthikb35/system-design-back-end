"""
01 — DSA Masterclass: Core Data Structures (from scratch)
=========================================================

Runnable companion to PDF Chapter "1+ — DSA Masterclass".

Implements, with demos and Big-O notes:
  * Singly & doubly linked lists (+ reverse, Floyd's cycle detection)
  * LRU cache (hash map + doubly linked list)  -> O(1) get/put
  * Stack (LIFO) & Queue (FIFO) & circular queue (ring buffer)
  * Binary Search Tree (insert/search + 4 traversals)
  * Min-heap operations via heapq (top-K)
  * Hash-table idea: Two Sum in O(n)

Run:  python data_structures.py
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass


# ===========================================================================
# LINKED LISTS
# ===========================================================================
@dataclass
class Node:
    val: int
    next: Node | None = None


def build_list(values: list[int]) -> Node | None:
    head: Node | None = None
    for v in reversed(values):
        head = Node(v, head)
    return head


def to_list(head: Node | None) -> list[int]:
    out: list[int] = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def reverse(head: Node | None) -> Node | None:
    """Reverse a singly linked list — O(n) time, O(1) space."""
    prev: Node | None = None
    while head:
        head.next, prev, head = prev, head, head.next
    return prev


def has_cycle(head: Node | None) -> bool:
    """Floyd's tortoise & hare — O(n) time, O(1) space."""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next          # type: ignore[union-attr]
        fast = fast.next.next
        if slow is fast:
            return True
    return False


# ===========================================================================
# LRU CACHE — hash map + doubly linked list => O(1) get/put
# ===========================================================================
class LRUCache:
    @dataclass
    class DNode:
        key: int = 0
        val: int = 0
        prev: LRUCache.DNode | None = None
        next: LRUCache.DNode | None = None

    def __init__(self, capacity: int) -> None:
        self.cap = capacity
        self.map: dict[int, LRUCache.DNode] = {}
        self.head = self.DNode()  # sentinel: most-recently-used side
        self.tail = self.DNode()  # sentinel: least-recently-used side
        self.head.next, self.tail.prev = self.tail, self.head

    def _remove(self, node: LRUCache.DNode) -> None:
        node.prev.next, node.next.prev = node.next, node.prev  # type: ignore[union-attr]

    def _push_front(self, node: LRUCache.DNode) -> None:
        node.prev, node.next = self.head, self.head.next
        self.head.next.prev = node  # type: ignore[union-attr]
        self.head.next = node

    def get(self, key: int) -> int:
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node)
        self._push_front(node)  # mark as most-recently-used
        return node.val

    def put(self, key: int, val: int) -> None:
        if key in self.map:
            self._remove(self.map[key])
        node = self.DNode(key, val)
        self.map[key] = node
        self._push_front(node)
        if len(self.map) > self.cap:  # evict least-recently-used
            lru = self.tail.prev
            self._remove(lru)          # type: ignore[arg-type]
            del self.map[lru.key]      # type: ignore[union-attr]


# ===========================================================================
# STACK / QUEUE / CIRCULAR QUEUE
# ===========================================================================
class Stack:
    """LIFO — O(1) push/pop."""

    def __init__(self) -> None:
        self._items: list[int] = []

    def push(self, v: int) -> None:
        self._items.append(v)

    def pop(self) -> int:
        return self._items.pop()

    def __len__(self) -> int:
        return len(self._items)


def is_balanced(s: str) -> bool:
    """Classic stack problem — balanced brackets, O(n)."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


class CircularQueue:
    """Fixed-size ring buffer — O(1) enqueue/dequeue, bounded memory."""

    def __init__(self, capacity: int) -> None:
        self.buf: list[int | None] = [None] * capacity
        self.cap = capacity
        self.head = self.size = 0

    def enqueue(self, v: int) -> bool:
        if self.size == self.cap:
            return False  # full
        self.buf[(self.head + self.size) % self.cap] = v
        self.size += 1
        return True

    def dequeue(self) -> int | None:
        if self.size == 0:
            return None
        v = self.buf[self.head]
        self.head = (self.head + 1) % self.cap
        self.size -= 1
        return v


# ===========================================================================
# BINARY SEARCH TREE
# ===========================================================================
@dataclass
class TreeNode:
    val: int
    left: TreeNode | None = None
    right: TreeNode | None = None


class BST:
    def __init__(self) -> None:
        self.root: TreeNode | None = None

    def insert(self, val: int) -> None:
        self.root = self._insert(self.root, val)

    def _insert(self, node: TreeNode | None, val: int) -> TreeNode:
        if node is None:
            return TreeNode(val)
        if val < node.val:
            node.left = self._insert(node.left, val)
        elif val > node.val:
            node.right = self._insert(node.right, val)
        return node

    def search(self, val: int) -> bool:
        node = self.root
        while node:
            if val == node.val:
                return True
            node = node.left if val < node.val else node.right
        return False

    def inorder(self) -> list[int]:
        out: list[int] = []

        def walk(n: TreeNode | None) -> None:
            if n:
                walk(n.left)
                out.append(n.val)  # left, node, right -> sorted for a BST
                walk(n.right)

        walk(self.root)
        return out

    def level_order(self) -> list[int]:
        out: list[int] = []
        q: deque[TreeNode] = deque([self.root] if self.root else [])
        while q:
            n = q.popleft()
            out.append(n.val)
            if n.left:
                q.append(n.left)
            if n.right:
                q.append(n.right)
        return out

    def height(self) -> int:
        def _h(node: TreeNode | None) -> int:
            return 0 if node is None else 1 + max(_h(node.left), _h(node.right))
        return _h(self.root)


# ===========================================================================
# HEAP (priority queue) + HASHING
# ===========================================================================
def k_largest(nums: list[int], k: int) -> list[int]:
    """Min-heap of size k -> O(n log k)."""
    heap: list[int] = []
    for n in nums:
        heapq.heappush(heap, n)
        if len(heap) > k:
            heapq.heappop(heap)
    return sorted(heap, reverse=True)


def two_sum(nums: list[int], target: int) -> tuple[int, int] | None:
    """Hash map turns O(n^2) into O(n)."""
    seen: dict[int, int] = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return (seen[target - n], i)
        seen[n] = i
    return None


def main() -> None:
    print("=" * 68)
    print("DSA MASTERCLASS — data_structures.py")
    print("=" * 68)

    head = build_list([10, 20, 30, 40])
    assert to_list(reverse(head)) == [40, 30, 20, 10]
    print("linked list reverse:", [40, 30, 20, 10])

    a, b, c = Node(1), Node(2), Node(3)
    a.next, b.next, c.next = b, c, a  # make a cycle
    assert has_cycle(a) is True
    assert has_cycle(build_list([1, 2, 3])) is False
    print("cycle detection (Floyd): cyclic=True, acyclic=False")

    lru = LRUCache(2)
    lru.put(1, 1)
    lru.put(2, 2)
    assert lru.get(1) == 1     # touch 1 -> 2 is now LRU
    lru.put(3, 3)              # evicts key 2
    assert lru.get(2) == -1 and lru.get(3) == 3
    print("LRU cache: evicted least-recently-used key 2")

    assert is_balanced("([]{})") and not is_balanced("([)]")
    print("stack: balanced-brackets check works")

    cq = CircularQueue(2)
    assert cq.enqueue(1) and cq.enqueue(2) and not cq.enqueue(3)
    assert cq.dequeue() == 1 and cq.enqueue(3)
    print("circular queue: wrap-around ring buffer works")

    bst = BST()
    for v in [50, 30, 70, 20, 40, 80]:
        bst.insert(v)
    assert bst.inorder() == [20, 30, 40, 50, 70, 80]  # sorted
    assert bst.level_order() == [50, 30, 70, 20, 40, 80]
    assert bst.search(40) and not bst.search(99)
    print("BST: inorder sorted + level-order BFS + search")

    assert k_largest([5, 1, 9, 2, 8], 3) == [9, 8, 5]
    print("heap: 3 largest ->", k_largest([5, 1, 9, 2, 8], 3))

    assert two_sum([2, 7, 11, 15], 9) == (0, 1)
    print("hashing: two-sum ->", two_sum([2, 7, 11, 15], 9))

    print("-" * 68)
    print("All data-structure demos passed ✔")


# ═══════════════════════════════════════════════════════════════════════════
# ═══  EXHAUSTIVE DSA NOTEBOOK — data structures gotchas  ═══════════════════
# ═══════════════════════════════════════════════════════════════════════════

import sys  # noqa: E402
import time  # noqa: E402


def sep(t): print(f"\n{'═'*64}\n  {t}\n{'═'*64}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §1 — LINKED LIST GOTCHAS
#
# Mental model
# ────────────
# A linked list is a chain of nodes where each node holds a value AND a
# pointer to the next node.  There is NO random access (unlike an array).
# O(1) insert/delete at a KNOWN position;  O(n) to FIND the position.
#
# When to use a linked list over a list/deque:
#   ✓ You're building from scratch a data structure that needs O(1)
#     splicing in the middle WITH a reference to the node (e.g. LRU cache)
#   ✗ For general-purpose queues prefer collections.deque (C-level, faster)
#   ✗ For stacks prefer list.append/pop (amortised O(1), cache-friendly)
#
# GOTCHA 1: Off-by-one in traversal / deletion — the hardest class of bug.
# GOTCHA 2: Losing the list by overwriting `head` before saving `head.next`.
# GOTCHA 3: Cycle detection — Floyd's two-pointer MUST start both at head.
# GOTCHA 4: Reversing in-place — need THREE pointers (prev, curr, next_node).
# GOTCHA 5: Sentinel nodes eliminate most null-check edge cases in doubly-LL.
# ──────────────────────────────────────────────────────────────────────────

def notebook_linked_list_gotchas() -> None:
    sep("§1 · Linked List Gotchas")

    # ── §1.1  Off-by-one in deletion ─────────────────────────────────────
    #
    # To DELETE a node at index i, you need a pointer to node at index i-1.
    # GOTCHA: if you advance `curr` to i before saving `curr.prev`, you lose
    # the link you need to re-attach.

    head = build_list([1, 2, 3, 4, 5])

    def delete_nth(head, n):
        """Delete node at 0-based index n.  Returns new head."""
        if n == 0:
            return head.next                     # special-case: remove head
        prev, curr = None, head
        for _ in range(n):
            prev, curr = curr, curr.next         # advance BOTH together
        prev.next = curr.next                    # skip over curr
        return head

    head = delete_nth(head, 2)   # remove index 2 (value 3)
    assert to_list(head) == [1, 2, 4, 5], to_list(head)
    print("Delete nth node: [1,2,3,4,5] remove idx-2 →", to_list(head))

    # ── §1.2  Reversing in-place — three-pointer technique ───────────────
    #
    # GOTCHA: you MUST save `curr.next` BEFORE overwriting `curr.next = prev`.
    # If you forget, you lose the rest of the list.

    head2 = build_list([1, 2, 3, 4, 5])
    # Wrong intuition: swap pairs iteratively without saving next_node
    def reverse_correct(h):
        prev, curr = None, h
        while curr:
            next_node = curr.next   # SAVE before overwrite
            curr.next = prev        # reverse the pointer
            prev, curr = curr, next_node
        return prev                 # prev is new head

    rev = reverse_correct(head2)
    assert to_list(rev) == [5, 4, 3, 2, 1]
    print("Reverse in-place: [1,2,3,4,5] →", to_list(rev))

    # ── §1.3  Floyd's cycle detection — why both start at head ───────────
    #
    # GOTCHA: if fast starts one step ahead, the algorithm can miss a cycle
    # of length 1 (single-node self-loop).  Always start BOTH at head.

    # Build a cycle: 1 → 2 → 3 → 4 → 2 (back to node 2)
    n1, n2, n3, n4 = Node(1), Node(2), Node(3), Node(4)
    n1.next, n2.next, n3.next, n4.next = n2, n3, n4, n2   # cycle!

    assert has_cycle(n1) is True
    assert has_cycle(build_list([1, 2, 3])) is False
    print("Floyd's cycle detection: cycle? True / no-cycle? False ✓")

    # ── §1.4  Sentinel nodes eliminate edge cases ─────────────────────────
    #
    # Mental model: use a "dummy" head node before the real head.
    # Then EVERY deletion is a "delete a non-head node" — no special-casing!

    class SentinelList:
        class Node:
            def __init__(self, v): self.v = v; self.next = None

        def __init__(self):
            self.dummy = self.Node(-1)   # sentinel — never removed
            self.dummy.next = None

        def prepend(self, v):
            n = self.Node(v)
            n.next = self.dummy.next
            self.dummy.next = n

        def delete_value(self, v):
            prev, curr = self.dummy, self.dummy.next
            while curr:
                if curr.v == v:
                    prev.next = curr.next   # uniform: no head special-case
                    return
                prev, curr = curr, curr.next

        def to_list(self):
            out, cur = [], self.dummy.next
            while cur:
                out.append(cur.v); cur = cur.next
            return out

    sl = SentinelList()
    for v in [5, 4, 3, 2, 1]: sl.prepend(v)
    sl.delete_value(1)   # delete head (no special case!)
    sl.delete_value(3)   # delete middle
    sl.delete_value(5)   # delete tail
    print("Sentinel list after deletes:", sl.to_list())   # [2, 4]

    # ── §1.5  When NOT to use a linked list ───────────────────────────────
    #
    # GOTCHA: Python linked lists are MUCH slower than deque/list in practice
    # because:
    #   1. Each Node is a separate heap allocation (Python object overhead ~56B)
    #   2. Pointer chasing kills CPU cache (cache miss per node)
    #   3. deque uses fixed-size blocks of pointers → far better cache locality

    n = 10_000
    ll = build_list(range(n))      # pure Python linked list

    t0 = time.perf_counter()
    cur = ll
    while cur: cur = cur.next
    t_ll = time.perf_counter() - t0

    dq = deque(range(n))
    t0 = time.perf_counter()
    for _ in dq: pass
    t_dq = time.perf_counter() - t0

    print(f"\nTraversal of {n} elements:")
    print(f"  Custom linked list: {t_ll*1000:.2f}ms")
    print(f"  collections.deque:  {t_dq*1000:.2f}ms  ← use this in production!")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §2 — LRU CACHE DEEP DIVE
#
# Mental model
# ────────────
# LRU = Least-Recently-Used eviction.
# Data structure = doubly-linked list (order) + hash map (O(1) lookup).
#   • get(key)  → O(1): hash map lookup + move node to front
#   • put(key)  → O(1): hash map insert + remove LRU tail if over capacity
#
# Why doubly linked (not singly)?
#   Eviction from the tail requires O(1) node removal.
#   To remove a node, you need BOTH prev and next pointers.
#   With singly-linked: you'd need O(n) to find the predecessor of the tail.
#
# GOTCHA 1: The sentinel head/tail trick — eliminates head==None edge cases.
# GOTCHA 2: When capacity is 1, put(existing_key) must still move to front.
# GOTCHA 3: Thread safety — LRUCache is NOT thread-safe; add a lock for concurrency.
# GOTCHA 4: In production use functools.lru_cache or cachetools.LRUCache.
# ──────────────────────────────────────────────────────────────────────────

def notebook_lru_gotchas() -> None:
    sep("§2 · LRU Cache Gotchas")

    # ── §2.1  Basic correctness ───────────────────────────────────────────
    cache = LRUCache(3)
    cache.put(1, 10); cache.put(2, 20); cache.put(3, 30)
    assert cache.get(1) == 10     # touches 1 → now MRU
    cache.put(4, 40)              # evicts 2 (LRU after 1 was touched)
    assert cache.get(2) == -1     # evicted ✓
    assert cache.get(3) == 30     # still present
    print("LRU basic correctness ✓")

    # ── §2.2  GOTCHA: update existing key must re-order ───────────────────
    cache2 = LRUCache(2)
    cache2.put(1, 1); cache2.put(2, 2)
    cache2.put(1, 100)            # UPDATE existing key 1 → must move to MRU
    cache2.put(3, 3)              # evicts 2 (LRU), NOT 1
    assert cache2.get(1) == 100   # 1 must still be here ✓
    assert cache2.get(2) == -1    # 2 was evicted ✓
    print("LRU update re-orders correctly ✓")

    # ── §2.3  GOTCHA: capacity 1 edge case ───────────────────────────────
    cache3 = LRUCache(1)
    cache3.put(1, 1)
    cache3.put(2, 2)              # evicts 1
    assert cache3.get(1) == -1   # evicted
    assert cache3.get(2) == 2    # present
    print("LRU capacity=1 edge case ✓")

    # ── §2.4  Production alternatives ─────────────────────────────────────
    from functools import lru_cache

    @lru_cache(maxsize=128)
    def expensive(n):
        return n * n

    _ = [expensive(i) for i in range(200)]
    info = expensive.cache_info()
    print(f"\nfunctools.lru_cache info: {info}")
    print("  Use functools.lru_cache for pure functions — C-level, thread-safe")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §3 — STACK & QUEUE GOTCHAS
#
# Mental model
# ────────────
# Stack (LIFO): push/pop from THE SAME END.
#   Uses: DFS, undo/redo, balanced brackets, call stack simulation.
# Queue (FIFO): enqueue at one end, dequeue from the other.
#   Uses: BFS, task scheduling, rate limiting, producer-consumer.
#
# GOTCHA 1: list.pop(0) for queue dequeue is O(n) — always use collections.deque.
# GOTCHA 2: Python's list.append/pop() is O(1) amortised for STACK use.
# GOTCHA 3: queue.Queue (thread-safe) vs deque (not thread-safe but faster).
# GOTCHA 4: Monotonic stack — a stack whose elements are always ordered;
#   used for "next greater element", histogram area, etc.
# ──────────────────────────────────────────────────────────────────────────

def notebook_stack_queue_gotchas() -> None:
    sep("§3 · Stack & Queue Gotchas")

    # ── §3.1  Balanced brackets (classic stack application) ───────────────
    def is_balanced(s):
        stack, pairs = [], {")":"(", "]":"[", "}":"{"}
        for ch in s:
            if ch in "([{":
                stack.append(ch)
            elif ch in ")]}":
                if not stack or stack[-1] != pairs[ch]:
                    return False
                stack.pop()
        return len(stack) == 0

    assert is_balanced("({[]})")
    assert not is_balanced("({[}])")
    assert is_balanced("")               # empty string is balanced
    assert not is_balanced("((")         # unclosed
    print("Balanced brackets: ✓")

    # ── §3.2  GOTCHA: list.pop(0) is O(n) ────────────────────────────────
    lst = list(range(5000))
    t0 = time.perf_counter()
    while lst: lst.pop(0)             # O(n) per pop  = O(n²) total
    t_list = time.perf_counter() - t0

    dq = deque(range(5000))
    t0 = time.perf_counter()
    while dq: dq.popleft()            # O(1) per pop  = O(n) total
    t_deque = time.perf_counter() - t0

    print(f"\nlist.pop(0) 5000×:    {t_list*1000:.2f}ms  (O(n²) total)")
    print(f"deque.popleft 5000×:  {t_deque*1000:.2f}ms  (O(n) total)")

    # ── §3.3  Monotonic stack — "next greater element" ───────────────────
    #
    # GOTCHA: people reach for O(n²) nested loops; monotonic stack is O(n).
    # Mental model: keep a stack of "candidates waiting for their answer".
    # When a new element is larger, it answers all smaller elements below it.

    def next_greater(nums):
        """For each element, find the next element to its right that is greater.
           Returns -1 if none exists.  O(n) time and space."""
        result = [-1] * len(nums)
        stack = []                         # stack of indices
        for i, n in enumerate(nums):
            while stack and nums[stack[-1]] < n:
                idx = stack.pop()
                result[idx] = n            # n is the next greater for idx
            stack.append(i)
        return result

    assert next_greater([2, 1, 2, 4, 3]) == [4, 2, 4, -1, -1]
    print("Monotonic stack next_greater([2,1,2,4,3]):", next_greater([2,1,2,4,3]))

    # ── §3.4  Largest rectangle in histogram ─────────────────────────────
    #
    # Classic stack problem — O(n) using monotonic increasing stack.
    def largest_rectangle(heights):
        stack, max_area = [], 0
        for i, h in enumerate(heights + [0]):   # append sentinel 0 to flush
            while stack and heights[stack[-1]] > h:
                height = heights[stack.pop()]
                width  = i if not stack else i - stack[-1] - 1
                max_area = max(max_area, height * width)
            stack.append(i)
        return max_area

    assert largest_rectangle([2,1,5,6,2,3]) == 10
    print("Largest rectangle in histogram:", largest_rectangle([2,1,5,6,2,3]))


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §4 — BINARY SEARCH TREE (BST) GOTCHAS
#
# Mental model
# ────────────
# BST property: left subtree < node < right subtree.
# Operations: O(h) where h = tree height.
#   Balanced tree:  h = O(log n)  → fast
#   Degenerate tree (sorted input): h = O(n)  → same as linked list!
#
# GOTCHA 1: Inserting sorted data into a BST creates a linked list O(n) not O(log n).
# GOTCHA 2: BST deletion with two children — replace with in-order SUCCESSOR
#   (minimum of right subtree) to preserve BST property.
# GOTCHA 3: In-order traversal of a BST gives elements in SORTED order.
#   Use this to verify BST correctness or to extract sorted elements.
# GOTCHA 4: Python has no built-in BST; use sortedcontainers.SortedList or
#   implement AVL/Red-Black for production.
# GOTCHA 5: Validating a BST — must pass min/max BOUNDS, not just compare
#   parent and child directly.
# ──────────────────────────────────────────────────────────────────────────

def notebook_bst_gotchas() -> None:
    sep("§4 · BST Gotchas")

    # ── §4.1  Degenerate tree on sorted input ─────────────────────────────
    bst_sorted = BST()
    for v in [1, 2, 3, 4, 5]:           # sorted input → O(n) height!
        bst_sorted.insert(v)

    bst_random = BST()
    for v in [3, 1, 5, 2, 4]:           # shuffled → O(log n) height
        bst_random.insert(v)

    h_sorted = bst_sorted.height()
    h_random = bst_random.height()
    print(f"Sorted-insert height:  {h_sorted}  (degenerate — same as linked list!)")
    print(f"Balanced-insert height:{h_random}  (O(log n))")

    # ── §4.2  In-order traversal = sorted output ──────────────────────────
    bst2 = BST()
    for v in [5, 3, 7, 1, 4, 6, 8, 2]: bst2.insert(v)
    inorder = bst2.inorder()
    assert inorder == sorted(inorder)
    print(f"\nIn-order traversal is always SORTED: {inorder}")

    # ── §4.3  GOTCHA: BST validation — need min/max bounds ───────────────
    #
    # Wrong approach: just check node > left child and node < right child.
    # This FAILS for:
    #       5
    #      / \
    #     1   4    <- 4 < 5 BUT 4 < 5 violates the BST property (4 should be
    #        / \      in the right subtree of 5, so must be > 5)
    #       3   6
    #
    # Correct: each node must be in the range (min_bound, max_bound).

    from dataclasses import dataclass as _dc
    @_dc
    class _N:
        key: int
        left: object = None
        right: object = None

    def is_valid_bst(root, lo=float('-inf'), hi=float('inf')):
        if root is None: return True
        v = root.val if hasattr(root, 'val') else root.key
        if not (lo < v < hi): return False
        return (is_valid_bst(root.left, lo, v) and
                is_valid_bst(root.right, v, hi))

    invalid_root = _N(4, _N(6, _N(1)), _N(7))   # 6 > 4 but on left → invalid!
    print(f"'Invalid' tree valid? {is_valid_bst(invalid_root)}")   # False ✓

    # ── §4.4  Why Python has no built-in BST ─────────────────────────────
    print("\nFor sorted ordered operations in Python:")
    print("  sortedcontainers.SortedList — O(log n) add/remove, O(1) index")
    print("  bisect module               — binary search on sorted lists")
    import bisect
    sl = [1, 3, 5, 7, 9]
    bisect.insort(sl, 4)   # insert 4 maintaining sorted order
    print(f"  bisect.insort([1,3,5,7,9], 4) = {sl}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §5 — HEAP / PRIORITY QUEUE GOTCHAS
#
# Mental model
# ────────────
# A heap is a COMPLETE binary tree satisfying the heap property:
#   Min-heap: parent ≤ both children (root = minimum element)
#   Max-heap: parent ≥ both children (root = maximum element)
# Python's heapq is a MIN-heap ONLY.  For max-heap: negate values.
#
# O(1) peek at minimum (heap[0])
# O(log n) push and pop
# O(n) heapify (build from list — NOT O(n log n)!)
#
# GOTCHA 1: heapq is NOT thread-safe; use queue.PriorityQueue for that.
# GOTCHA 2: heapq.nlargest(k, it) is O(n log k), not O(n log n) — use it!
# GOTCHA 3: Heap elements must be comparable; for custom objects use a tuple
#   (priority, tiebreaker, item) to avoid TypeError on equal priorities.
# GOTCHA 4: Modifying an element already in the heap corrupts the heap property.
#   Use the "lazy deletion" pattern instead.
# ──────────────────────────────────────────────────────────────────────────

def notebook_heap_gotchas() -> None:
    sep("§5 · Heap / Priority Queue Gotchas")

    import heapq

    # ── §5.1  Max-heap via negation ───────────────────────────────────────
    nums = [3, 1, 4, 1, 5, 9, 2, 6]
    max_heap = [-x for x in nums]
    heapq.heapify(max_heap)
    max_val = -heapq.heappop(max_heap)
    print(f"Max-heap via negation: max of {nums} = {max_val}")   # 9

    # ── §5.2  GOTCHA: equal priorities need tiebreaker ────────────────────
    from dataclasses import dataclass

    @dataclass(order=False)
    class Task:
        name: str
        priority: int

    # This would raise TypeError if two tasks have equal priority:
    # heapq.heappush(h, Task("a",1)); heapq.heappush(h, Task("b",1))
    # Fix: wrap in a tuple (priority, counter, task)

    counter = 0
    heap = []
    for t in [Task("low",3), Task("high",1), Task("med",2), Task("also-high",1)]:
        heapq.heappush(heap, (t.priority, counter, t))   # counter breaks ties
        counter += 1

    ordered = []
    while heap:
        _, _, task = heapq.heappop(heap)
        ordered.append(task.name)
    print(f"Priority order (ties by insertion): {ordered}")

    # ── §5.3  GOTCHA: heapify is O(n), not O(n log n) ────────────────────
    #
    # Floyd's algorithm: start from the last non-leaf and sift down.
    # Each sift-down is O(log k) for a subtree of size k.
    # Total: Σ O(h_i) for all nodes = O(n) (most nodes have small subtrees).

    big = list(range(100_000, 0, -1))   # reversed = worst case for sorting
    t0 = time.perf_counter()
    heapq.heapify(big)
    print(f"\nheapify(100k elements): {(time.perf_counter()-t0)*1000:.2f}ms — O(n)")

    # ── §5.4  Top-K pattern — O(n log k), better than sort O(n log n) ─────
    import heapq
    data = list(range(1, 1_000_001))   # 1M elements
    t0 = time.perf_counter()
    top_k = heapq.nlargest(10, data)
    t_heap = time.perf_counter() - t0

    t0 = time.perf_counter()
    top_k_sort = sorted(data, reverse=True)[:10]
    t_sort = time.perf_counter() - t0

    assert top_k == top_k_sort
    print("\nTop-10 from 1M elements:")
    print(f"  heapq.nlargest: {t_heap*1000:.2f}ms  (O(n log k))")
    print(f"  sort+slice:     {t_sort*1000:.2f}ms  (O(n log n))")
    print(f"  nlargest is {t_sort/t_heap:.1f}× faster for small k")

    # ── §5.5  Lazy deletion pattern ───────────────────────────────────────
    #
    # GOTCHA: you can't remove/update an arbitrary element from a heap.
    # Pattern: mark it as "deleted" in a set; skip when popping.

    heap2 = []
    deleted = set()
    uid = 0

    def push(priority, item):
        nonlocal uid
        entry = (priority, uid, item)
        heapq.heappush(heap2, entry)
        uid += 1
        return entry

    def remove(entry):
        deleted.add(entry)   # mark as deleted

    def pop():
        while heap2:
            entry = heapq.heappop(heap2)
            if entry not in deleted:
                return entry[2]   # return item
        return None

    e1 = push(3, "task-C"); push(1, "task-A"); push(2, "task-B")
    remove(e1)   # "cancel" task-C without heap restructure
    results = [pop() for _ in range(2)]
    print(f"\nLazy deletion: {results}")   # ['task-A', 'task-B']


def run_data_structures_notebook() -> None:
    notebook_linked_list_gotchas()
    notebook_lru_gotchas()
    notebook_stack_queue_gotchas()
    notebook_bst_gotchas()
    notebook_heap_gotchas()
    print("\n" + "═"*64)
    print("  DATA STRUCTURES NOTEBOOK COMPLETE")
    print("═"*64)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
    run_data_structures_notebook()

