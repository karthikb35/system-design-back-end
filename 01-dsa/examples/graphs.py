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


# ═══════════════════════════════════════════════════════════════════════════
# ═══  EXHAUSTIVE NOTEBOOK — graph algorithm gotchas  ═══════════════════════
# ═══════════════════════════════════════════════════════════════════════════

import sys
from collections import deque

def sep(t): print(f"\n{'═'*64}\n  {t}\n{'═'*64}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §G1 — BFS vs DFS GOTCHAS
#
# Mental model
# ────────────
# BFS  = explore LEVEL BY LEVEL using a QUEUE.
#   → Guarantees SHORTEST PATH (fewest edges) in unweighted graphs.
#   → Memory: O(V) frontier can hold many nodes at wide levels.
# DFS  = explore DEPTH FIRST using a STACK (or recursion).
#   → Does NOT guarantee shortest path.
#   → Memory: O(depth) for iterative; O(depth) call stack for recursive.
#   → Risk: RecursionError for deep/adversarial graphs.
#
# GOTCHA 1: BFS needs a `visited` set BEFORE enqueuing, not after dequeuing.
#   Without it, the same node gets added to the queue multiple times → O(V²).
# GOTCHA 2: DFS via recursion will crash on large/deep graphs (RecursionError).
#   Use iterative DFS with an explicit stack for production code.
# GOTCHA 3: BFS/DFS on an undirected graph: mark edges bidirectional.
#   On directed: mark each direction separately.
# GOTCHA 4: For shortest path WITH WEIGHTS, BFS gives wrong answer. Use Dijkstra.
# ──────────────────────────────────────────────────────────────────────────

def notebook_bfs_dfs_gotchas() -> None:
    sep("§G1 · BFS / DFS Gotchas")

    # ── §G1.1  GOTCHA: visited BEFORE enqueue ─────────────────────────────
    def bfs_wrong(graph, start):
        """Marks visited AFTER dequeue — allows duplicates in queue."""
        visited, order, queue = set(), [], deque([start])
        while queue:
            node = queue.popleft()
            if node in visited: continue       # late check: many duplicates already queued
            visited.add(node)
            order.append(node)
            for neighbor in graph.get(node, []):
                queue.append(neighbor)         # adds duplicates!
        return order

    def bfs_correct(graph, start):
        """Marks visited BEFORE enqueue — no duplicates in queue."""
        visited = {start}
        order, queue = [], deque([start])
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)      # mark before enqueue ← key!
                    queue.append(neighbor)
        return order

    g = {"A":["B","C"], "B":["D","E"], "C":["F"], "D":[], "E":[], "F":[]}
    order_w = bfs_wrong(g, "A")
    order_c = bfs_correct(g, "A")
    print(f"BFS wrong (late mark): {order_w}  ← same result here but duplicates queued")
    print(f"BFS correct (early mark): {order_c}")
    assert set(order_w) == set(order_c)   # same nodes visited, but wrong is less efficient

    # ── §G1.2  BFS for shortest path ──────────────────────────────────────
    def shortest_path(graph, src, dst):
        if src == dst: return [src]
        parent = {src: None}
        queue = deque([src])
        while queue:
            node = queue.popleft()
            for nb in graph.get(node, []):
                if nb not in parent:
                    parent[nb] = node
                    if nb == dst:
                        path = []
                        while nb is not None:
                            path.append(nb); nb = parent[nb]
                        return path[::-1]
                    queue.append(nb)
        return []   # no path

    path = shortest_path(g, "A", "E")
    print(f"\nShortest path A→E: {path} (length {len(path)-1} edges)")

    # ── §G1.3  GOTCHA: DFS recursion depth limit ───────────────────────────
    # Build a long chain: 0→1→2→...→999
    deep_graph = {i: [i+1] for i in range(999)}
    deep_graph[999] = []

    # Iterative DFS is safe for any depth
    def dfs_iterative(graph, start):
        visited, order, stack = set(), [], [start]
        while stack:
            node = stack.pop()
            if node in visited: continue
            visited.add(node); order.append(node)
            for nb in reversed(graph.get(node, [])):
                if nb not in visited: stack.append(nb)
        return order

    traversal = dfs_iterative(deep_graph, 0)
    print(f"\nIterative DFS on chain of 1000: visited {len(traversal)} nodes (no RecursionError)")

    # ── §G1.4  BFS for level-order / multi-source ────────────────────────
    def multi_source_bfs(graph, sources):
        """Start BFS from MULTIPLE sources simultaneously."""
        dist = {s: 0 for s in sources}
        queue = deque(sources)
        while queue:
            node = queue.popleft()
            for nb in graph.get(node, []):
                if nb not in dist:
                    dist[nb] = dist[node] + 1
                    queue.append(nb)
        return dist

    # Example: distance from EITHER A or F
    dists = multi_source_bfs(g, ["A", "F"])
    print(f"\nMulti-source BFS from A,F: {dists}")


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §G2 — DIJKSTRA GOTCHAS
#
# Mental model
# ────────────
# Dijkstra = BFS with a PRIORITY QUEUE instead of a regular queue.
# Each pop gives the CLOSEST unprocessed node.
# Greedy: once a node is popped (settled), its shortest distance is final.
#
# GOTCHA 1: NEGATIVE EDGE WEIGHTS break Dijkstra.
#   Dijkstra's greedy assumption fails: a settled node might later get a
#   shorter path through a negative edge. Use Bellman-Ford instead.
# GOTCHA 2: Stale entries in the heap (lazy deletion pattern).
#   When a node's distance is relaxed, the OLD entry in the heap is not removed.
#   Check: if popped distance > current known distance, skip it.
# GOTCHA 3: O((V + E) log V) time — the log V comes from the heap operations.
# GOTCHA 4: For DENSE graphs (E ≈ V²), an adjacency matrix with a linear scan
#   (Prim's algorithm style) can be faster in practice.
# ──────────────────────────────────────────────────────────────────────────

def notebook_dijkstra_gotchas() -> None:
    sep("§G2 · Dijkstra Gotchas")

    # ── §G2.1  Correct Dijkstra (handles stale heap entries) ──────────────
    import heapq

    def dijkstra_correct(graph, src):
        dist = {node: float('inf') for node in graph}
        dist[src] = 0
        heap = [(0, src)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]: continue   # STALE entry — skip!
            for v, w in graph.get(u, []):
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    heapq.heappush(heap, (dist[v], v))
        return dist

    wg = {"A":[("B",1),("C",4)], "B":[("C",2),("D",5)],
          "C":[("D",1)], "D":[]}
    print("Dijkstra:", dijkstra_correct(wg, "A"))

    # ── §G2.2  GOTCHA: negative weights break Dijkstra ────────────────────
    neg_graph = {"A":[("B",3),("C",2)], "B":[("C",-4)], "C":[("D",1)], "D":[]}
    # Shortest A→C: A→B→C = 3+(-4) = -1 (NOT 2 via direct A→C edge!)
    # Dijkstra would settle C with dist=2 and never update it via B:

    wrong = dijkstra_correct(neg_graph, "A")
    print(f"\nNegative weight A→C: Dijkstra gives {wrong['C']} (WRONG, should be -1)")
    print("Use Bellman-Ford for graphs with negative edges")

    # ── §G2.3  Bellman-Ford handles negative edges ────────────────────────
    def bellman_ford(graph, src):
        """O(V*E) — correct for negative edges, detects negative cycles."""
        dist = {n: float('inf') for n in graph}
        dist[src] = 0
        nodes = list(graph.keys())
        for _ in range(len(nodes) - 1):   # relax V-1 times
            for u in graph:
                for v, w in graph[u]:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
        # Check for negative cycle: if any edge still relaxes, cycle exists
        for u in graph:
            for v, w in graph[u]:
                if dist[u] + w < dist[v]:
                    return None   # negative cycle detected!
        return dist

    bf_dist = bellman_ford(neg_graph, "A")
    print(f"Bellman-Ford A→C: {bf_dist['C']}  ← correct!")  # -1


# ──────────────────────────────────────────────────────────────────────────
# NOTEBOOK §G3 — CYCLE DETECTION & TOPOLOGICAL SORT GOTCHAS
#
# Mental model
# ────────────
# Directed cycle detection: DFS with THREE colours.
#   WHITE (unvisited) → GREY (in current path) → BLACK (done)
#   If DFS encounters a GREY node → back edge → cycle!
#
# Undirected cycle detection: DFS + track parent.
#   If DFS encounters a visited node that is NOT the parent → cycle!
#
# Topological sort: only valid for DAGs (Directed Acyclic Graphs).
# GOTCHA 1: topo sort on a cyclic graph → incomplete ordering (Kahn) or
#           infinite loop (naive DFS). Always check for cycles first.
# GOTCHA 2: Multiple valid topological orderings can exist.
# GOTCHA 3: Kahn's algorithm (BFS-based) detects cycles naturally:
#   if the result has fewer nodes than the graph, a cycle exists.
# ──────────────────────────────────────────────────────────────────────────

def notebook_cycle_topo_gotchas() -> None:
    sep("§G3 · Cycle Detection & Topological Sort Gotchas")

    # ── §G3.1  Directed cycle detection ───────────────────────────────────
    dag   = {"A":["B","C"], "B":["D"], "C":["D"], "D":[]}
    cycle = {"A":["B"], "B":["C"], "C":["A"]}  # A→B→C→A

    assert not has_cycle_directed(dag)
    assert has_cycle_directed(cycle)
    print("Directed cycle detection: DAG=no-cycle, cyclic=cycle ✓")

    # ── §G3.2  Kahn's topological sort detects cycles ────────────────────
    def kahn_topo(graph):
        from collections import defaultdict, deque
        in_degree = defaultdict(int)
        for u in graph:
            for v in graph[u]:
                in_degree[v] += 1
        queue = deque(u for u in graph if in_degree[u] == 0)
        order = []
        while queue:
            u = queue.popleft(); order.append(u)
            for v in graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0: queue.append(v)
        # If order is shorter than graph, a cycle exists
        return order if len(order) == len(graph) else None

    topo = kahn_topo(dag)
    print(f"\nTopological sort of DAG: {topo}")

    topo_cyclic = kahn_topo(cycle)
    print(f"Topo sort of cyclic graph: {topo_cyclic}  ← None = cycle detected!")

    # ── §G3.3  Undirected cycle detection (union-find) ────────────────────
    def has_cycle_undirected(nodes, edges):
        """Union-Find (disjoint sets) for undirected cycle detection."""
        parent = {n: n for n in nodes}
        rank   = {n: 0 for n in nodes}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # path compression
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry: return False   # same component → cycle!
            if rank[rx] < rank[ry]: rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]: rank[rx] += 1
            return True

        for u, v in edges:
            if not union(u, v): return True
        return False

    nodes_uc  = ["A","B","C","D"]
    edges_no  = [("A","B"),("B","C"),("C","D")]
    edges_yes = [("A","B"),("B","C"),("C","A")]

    print(f"\nUndirected cycle: linear chain = {has_cycle_undirected(nodes_uc, edges_no)}")   # False
    print(f"Undirected cycle: triangle     = {has_cycle_undirected(['A','B','C'], edges_yes)}")  # True


def run_graph_notebook() -> None:
    notebook_bfs_dfs_gotchas()
    notebook_dijkstra_gotchas()
    notebook_cycle_topo_gotchas()
    print("\n" + "═"*64)
    print("  GRAPH NOTEBOOK COMPLETE")
    print("═"*64)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
    run_graph_notebook()

