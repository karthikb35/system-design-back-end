"""
01 — DSA Internals: Trie (Prefix Tree) From Scratch
===================================================

Runnable companion to PDF Book II "The data structure behind autocomplete".

A hash set answers "is this exact word present?" in O(L). A TRIE answers
PREFIX questions — "which words start with 'pre'?" — which a hash set can't do
without scanning everything. Each node is a character; a path from the root
spells a prefix; a flag marks the end of a real word.

Costs (L = length of the key, NOT the number of words):
    insert / search / starts_with : O(L)
    autocomplete                  : O(L + size of the matching subtree)

Used in autocomplete, spell-check, IP routing tables, and T9 text entry.
"""

from __future__ import annotations


class _TrieNode:
    __slots__ = ("children", "is_word")

    def __init__(self):
        self.children: dict[str, _TrieNode] = {}
        self.is_word = False


class Trie:
    def __init__(self):
        self._root = _TrieNode()
        self._size = 0

    def insert(self, word: str) -> None:
        node = self._root
        for ch in word:
            node = node.children.setdefault(ch, _TrieNode())
        if not node.is_word:
            node.is_word = True
            self._size += 1

    def _find(self, prefix: str) -> _TrieNode | None:
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def search(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._find(prefix) is not None

    def autocomplete(self, prefix: str) -> list[str]:
        """All stored words beginning with `prefix`, in sorted order."""
        node = self._find(prefix)
        if node is None:
            return []
        out: list[str] = []
        self._collect(node, prefix, out)
        return sorted(out)

    def _collect(self, node: _TrieNode, path: str, out: list[str]) -> None:
        if node.is_word:
            out.append(path)
        for ch, child in node.children.items():
            self._collect(child, path + ch, out)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, word: str) -> bool:
        return self.search(word)


def demo() -> None:
    words = ["cat", "car", "card", "care", "dog", "dodge", "do", "care"]  # dup 'care'
    trie = Trie()
    for w in words:
        trie.insert(w)

    assert len(trie) == 7, "7 unique words; duplicate 'care' counted once"
    assert trie.search("car") and trie.search("card")
    assert not trie.search("ca"), "'ca' is a prefix, not a stored word"
    assert trie.starts_with("ca") and trie.starts_with("do")
    assert not trie.starts_with("xyz")
    print("   inserted", sorted(set(words)))
    print("   search('car') =", trie.search("car"), " starts_with('ca') =", trie.starts_with("ca"))

    # Autocomplete — the thing a hash set fundamentally cannot do in O(L).
    assert trie.autocomplete("car") == ["car", "card", "care"]
    assert trie.autocomplete("do") == ["do", "dodge", "dog"]
    assert trie.autocomplete("z") == []
    print("   autocomplete('car') =", trie.autocomplete("car"))
    print("   autocomplete('do')  =", trie.autocomplete("do"))


def main() -> None:
    print("=" * 70)
    print("DSA INTERNALS — tries.py (prefix tree)")
    print("=" * 70)
    print("Character-per-node tree; insert/search/starts_with are O(L):")
    demo()
    print("-" * 70)
    print("Lesson: a trie trades memory for O(L) PREFIX queries a hash set can't answer. Autocomplete/routing.")
    print("All tries demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
