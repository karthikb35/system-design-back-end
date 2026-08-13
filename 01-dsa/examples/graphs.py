"""
01 — DSA Masterclass: Graphs & Graph Algorithms
===============================================

Runnable companion to PDF Chapter "1+ — DSA Masterclass" (graph section).

  * Adjacency-list representation
  * BFS (shortest path in unweighted graph) & DFS
  * Number of islands (grid as a graph)
  * Cycle detection (directed)
  * Topological sort (Kahn's algorithm)
  * Dijkstra's shortest path (weighted, non-negative)
  * Minimum Spanning Tree (Kruskal's with union-find)

Run:  python graphs.py
"""

from __future__ import annotations

import heapq
from collections import defaultdict, deque

Graph = dict[str, list[str]]
Weighted = dict[str, list[tuple[str, int]]]


# ===========================================================================
# BFS / DFS
# ===========================================================================
def bfs(graph: Graph, start: str) -> list[str]:
    seen, order, q = {start}, [], deque([start])
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return order


def dfs(graph: Graph, start: str) -> list[str]:
    seen: set[str] = set()
    order: list[str] = []

    def walk(node: str) -> None:
        seen.add(node)
        order.append(node)
        for nxt in graph.get(node, []):
            if nxt not in seen:
                walk(nxt)

    walk(start)
    return order


def shortest_unweighted(graph: Graph, start: str, goal: str) -> int:
    """BFS gives the fewest edges between two nodes."""
    q: deque[tuple[str, int]] = deque([(start, 0)])
    seen = {start}
    while q:
        node, dist = q.popleft()
        if node == goal:
            return dist
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, dist + 1))
    return -1


# ===========================================================================
# NUMBER OF ISLANDS — grid as an implicit graph
# ===========================================================================
def num_islands(grid: list[list[str]]) -> int:
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()

    def sink(r: int, c: int) -> None:
        stack = [(r, c)]
        while stack:
            i, j = stack.pop()
            if 0 <= i < rows and 0 <= j < cols and (i, j) not in seen and grid[i][j] == "1":
                seen.add((i, j))
                stack.extend([(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)])

    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and (r, c) not in seen:
                count += 1
                sink(r, c)
    return count


# ===========================================================================
# DIRECTED CYCLE DETECTION + TOPOLOGICAL SORT
# ===========================================================================
def has_cycle_directed(graph: Graph) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)

    def visit(node: str) -> bool:
        color[node] = GRAY
        for nxt in graph.get(node, []):
            if color[nxt] == GRAY:      # back-edge to in-progress node -> cycle
                return True
            if color[nxt] == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in graph)


def topological_sort(graph: Graph) -> list[str]:
    """Kahn's algorithm — empty result signals a cycle (not a DAG)."""
    indegree: dict[str, int] = {n: 0 for n in graph}
    for node in graph:
        for nxt in graph[node]:
            indegree[nxt] = indegree.get(nxt, 0) + 1
            indegree.setdefault(node, indegree.get(node, 0))
    q = deque([n for n, d in indegree.items() if d == 0])
    order: list[str] = []
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph.get(node, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)
    return order if len(order) == len(indegree) else []


# ===========================================================================
# DIJKSTRA — weighted shortest path (non-negative edges)
# ===========================================================================
def dijkstra(graph: Weighted, start: str) -> dict[str, int]:
    dist: dict[str, int] = {start: 0}
    pq: list[tuple[int, str]] = [(0, start)]
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist.get(node, float("inf")):
            continue
        for nbr, w in graph.get(node, []):
            nd = d + w
            if nd < dist.get(nbr, float("inf")):
                dist[nbr] = nd
                heapq.heappush(pq, (nd, nbr))
    return dist


# ===========================================================================
# MINIMUM SPANNING TREE — Kruskal + union-find
# ===========================================================================
class UnionFind:
    def __init__(self, nodes: list[str]) -> None:
        self.parent = {n: n for n in nodes}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path compression
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False  # would form a cycle
        self.parent[ra] = rb
        return True


def kruskal_mst(nodes: list[str], edges: list[tuple[int, str, str]]) -> int:
    """Return total weight of the MST. edges = (weight, u, v)."""
    uf = UnionFind(nodes)
    total = 0
    for weight, u, v in sorted(edges):  # cheapest first
        if uf.union(u, v):
            total += weight
    return total


def main() -> None:
    print("=" * 68)
    print("DSA MASTERCLASS — graphs.py")
    print("=" * 68)

    g: Graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    assert bfs(g, "A") == ["A", "B", "C", "D"]
    assert dfs(g, "A")[0] == "A" and set(dfs(g, "A")) == {"A", "B", "C", "D"}
    assert shortest_unweighted(g, "A", "D") == 2
    print("BFS/DFS + shortest unweighted path A->D =", shortest_unweighted(g, "A", "D"))

    grid = [
        list("11000"),
        list("11000"),
        list("00100"),
        list("00011"),
    ]
    assert num_islands(grid) == 3
    print("islands: found", num_islands(grid))

    dag: Graph = {"shirt": ["tie"], "tie": ["jacket"], "belt": ["jacket"], "jacket": []}
    order = topological_sort(dag)
    assert order.index("shirt") < order.index("tie") < order.index("jacket")
    assert not has_cycle_directed(dag)
    cyclic: Graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
    assert has_cycle_directed(cyclic) and topological_sort(cyclic) == []
    print("topological sort:", order, "| cycle detected in cyclic graph")

    wg: Weighted = {
        "A": [("B", 1), ("C", 4)],
        "B": [("C", 2), ("D", 5)],
        "C": [("D", 1)],
        "D": [],
    }
    assert dijkstra(wg, "A") == {"A": 0, "B": 1, "C": 3, "D": 4}
    print("dijkstra from A:", dijkstra(wg, "A"))

    nodes = ["A", "B", "C", "D"]
    edges = [(1, "A", "B"), (4, "A", "C"), (2, "B", "C"), (5, "B", "D"), (1, "C", "D")]
    assert kruskal_mst(nodes, edges) == 4  # A-B(1) + B-C(2) + C-D(1)
    print("MST total weight (Kruskal):", kruskal_mst(nodes, edges))

    print("-" * 68)
    print("All graph demos passed ✔")


if __name__ == "__main__":
    # Keep Unicode output safe even when stdout is redirected/piped (Windows cp1252 fallback).
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
