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


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
