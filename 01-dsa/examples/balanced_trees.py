"""
01 — DSA Internals: Balanced Trees (AVL) From Scratch
=====================================================

Runnable companion to PDF Book II "Why a plain BST isn't enough".

A Binary Search Tree gives O(log n) search — but ONLY if it stays balanced.
Insert sorted data into a naive BST and it degenerates into a linked list:
O(n). An AVL tree fixes this by keeping every node's subtree heights within 1,
performing ROTATIONS after each insert to restore balance.

This file builds an AVL tree and PROVES the height stays ~log2(n) even for the
worst-case input (already-sorted keys), where a naive BST would be height n-1.

The four rotation cases:
    LL  -> right rotate
    RR  -> left rotate
    LR  -> left rotate child, then right rotate
    RL  -> right rotate child, then left rotate
"""

from __future__ import annotations

import math


class _Node:
    __slots__ = ("key", "left", "right", "height")

    def __init__(self, key):
        self.key = key
        self.left: _Node | None = None
        self.right: _Node | None = None
        self.height = 1


def _h(n: _Node | None) -> int:
    return n.height if n else 0


def _balance(n: _Node | None) -> int:
    return _h(n.left) - _h(n.right) if n else 0


def _update(n: _Node) -> None:
    n.height = 1 + max(_h(n.left), _h(n.right))


def _rotate_right(y: _Node) -> _Node:
    x = y.left
    assert x is not None
    y.left = x.right
    x.right = y
    _update(y)
    _update(x)
    return x                                # x is the new subtree root


def _rotate_left(x: _Node) -> _Node:
    y = x.right
    assert y is not None
    x.right = y.left
    y.left = x
    _update(x)
    _update(y)
    return y


class AVLTree:
    def __init__(self):
        self._root: _Node | None = None
        self._size = 0

    def insert(self, key) -> None:
        inserted = [False]
        self._root = self._insert(self._root, key, inserted)
        if inserted[0]:
            self._size += 1

    def _insert(self, node: _Node | None, key, inserted) -> _Node:
        if node is None:
            inserted[0] = True
            return _Node(key)
        if key < node.key:
            node.left = self._insert(node.left, key, inserted)
        elif key > node.key:
            node.right = self._insert(node.right, key, inserted)
        else:
            return node                     # duplicate key: ignore

        _update(node)
        bal = _balance(node)

        if bal > 1 and key < node.left.key:            # LL
            return _rotate_right(node)
        if bal < -1 and key > node.right.key:          # RR
            return _rotate_left(node)
        if bal > 1 and key > node.left.key:            # LR
            node.left = _rotate_left(node.left)
            return _rotate_right(node)
        if bal < -1 and key < node.right.key:          # RL
            node.right = _rotate_right(node.right)
            return _rotate_left(node)
        return node

    def __contains__(self, key) -> bool:
        n = self._root
        while n:
            if key == n.key:
                return True
            n = n.left if key < n.key else n.right
        return False

    def height(self) -> int:
        return _h(self._root)

    def inorder(self) -> list:
        out: list = []
        self._walk(self._root, out)
        return out

    def _walk(self, n: _Node | None, out: list) -> None:
        if n:
            self._walk(n.left, out)
            out.append(n.key)
            self._walk(n.right, out)

    def is_balanced(self) -> bool:
        def check(n: _Node | None) -> bool:
            if n is None:
                return True
            return abs(_balance(n)) <= 1 and check(n.left) and check(n.right)
        return check(self._root)

    def __len__(self) -> int:
        return self._size


def demo() -> None:
    # WORST CASE for a naive BST: already-sorted keys would form a chain of
    # height n-1. AVL keeps height near log2(n).
    n = 1000
    tree = AVLTree()
    for k in range(n):
        tree.insert(k)

    assert len(tree) == n
    assert tree.inorder() == list(range(n)), "in-order traversal must be sorted"
    assert tree.is_balanced(), "every node must satisfy the AVL invariant"

    naive_bst_height = n            # sorted insert into plain BST -> ~n
    log_n = math.log2(n)
    assert tree.height() <= 1.5 * log_n, "AVL height must stay near log2(n)"
    print(f"   inserted {n} SORTED keys")
    print(f"   naive BST would be height ~{naive_bst_height};  AVL height = {tree.height()} (log2 n = {log_n:.1f})")

    assert 500 in tree and n not in tree
    print("   search, balance invariant, and sorted traversal all verified")


def main() -> None:
    print("=" * 70)
    print("DSA INTERNALS — balanced_trees.py (AVL)")
    print("=" * 70)
    print("Self-balancing BST via rotations (LL / RR / LR / RL):")
    demo()
    print("-" * 70)
    print("Lesson: a plain BST degrades to O(n) on sorted input; AVL rotations keep it O(log n).")
    print("All balanced_trees demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
