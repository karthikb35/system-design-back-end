#!/usr/bin/env python3
"""
reorganize_notebooks.py
=======================
Splits the bulky consolidated notebooks into concept-level notebooks.
Each output notebook covers ONE concept exhaustively:
  theory + implementation + gotchas + real-world scenarios + interview Q&A

Output structure
─────────────────
01-dsa/examples/
  linked_list.ipynb            (singly + doubly + LRU cache + real-world)
  stack_queue.ipynb            (LIFO/FIFO + monotonic stack + real-world)
  binary_search_tree.ipynb     (BST + AVL + traversals + real-world)
  heap_priority_queue.ipynb    (min/max heap + heapq + top-K + real-world)
  hash_table.ipynb             (hash map from scratch + collision + real-world)
  trie.ipynb                   (prefix tree + autocomplete + real-world)
  sorting_searching.ipynb      (all sorts + binary search + real-world)
  graphs.ipynb                 (BFS/DFS/Dijkstra/topo + cycle detect + real-world)
  recursion_dp.ipynb           (recursion + DP + greedy + backtracking + real-world)
  bit_manipulation.ipynb       (all bit ops + use cases)

00-python-foundations/
  py_types_collections.ipynb   (types + mutability + aliasing + all 4 collections)
  py_functions_closures.ipynb  (functions + closures + decorators + comprehensions)
  py_oop.ipynb                 (4 pillars + MRO + protocols + dataclasses)
  py_iterators_generators.ipynb (iterator protocol + generators + context managers)
  py_advanced.ipynb            (descriptors + metaclasses + typing + memory)

02-solid/examples/
  solid_complete.ipynb         (stays as-is — right granularity)

03-design-patterns/examples/
  creational_patterns.ipynb    (Factory + Abstract Factory + Builder + Prototype + Singleton)
  structural_patterns.ipynb    (Adapter + Bridge + Composite + Decorator + Facade + Flyweight + Proxy)
  behavioral_patterns.ipynb    (Strategy + Observer + Command + Chain + State + Template + Visitor + rest)
  resilience_patterns.ipynb    (Circuit Breaker + Retry + Backoff + production patterns)

Run: python reorganize_notebooks.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).parent


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def load_nb(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cell_source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def is_divider(cell: dict) -> bool:
    src = cell_source(cell).strip()
    return src.startswith("---") and cell["cell_type"] == "markdown"


def title_from_divider(cell: dict) -> str:
    src = cell_source(cell).strip()
    lines = [l.strip() for l in src.split("\n") if l.strip() and not l.startswith("---")]
    if lines:
        return lines[0].lstrip("#").strip()
    return ""


def split_at_dividers(nb: dict) -> list[tuple[str, list[dict]]]:
    """Returns [(section_title, cells_in_section), ...]"""
    sections: list[tuple[str, list[dict]]] = []
    current_title = "Introduction"
    current_cells: list[dict] = []

    for cell in nb["cells"]:
        if is_divider(cell):
            if current_cells:
                sections.append((current_title, current_cells))
            current_title  = title_from_divider(cell)
            current_cells  = []
        else:
            if cell_source(cell).strip():
                current_cells.append(dict(cell, id=new_id()))

    if current_cells:
        sections.append((current_title, current_cells))

    return sections


def header_cell(title: str, subtitle: str = "") -> dict:
    src = f"# {title}\n"
    if subtitle:
        src += f"\n*{subtitle}*\n"
    return {"cell_type": "markdown", "id": new_id(), "metadata": {}, "source": [src]}


def section_header(title: str) -> dict:
    return {"cell_type": "markdown", "id": new_id(), "metadata": {},
            "source": [f"---\n## {title}\n"]}


def write_nb(cells: list[dict], path: Path) -> None:
    nb = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "cells": [dict(c, id=new_id()) for c in cells if cell_source(c).strip()],
    }
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓  {path.name:55s} ({len(nb['cells'])} cells, {path.stat().st_size//1024}KB)")


def build_notebook(title: str, subtitle: str,
                   sections: list[tuple[str, list[dict]]]) -> list[dict]:
    cells: list[dict] = [header_cell(title, subtitle)]
    for sec_title, sec_cells in sections:
        cells.append(section_header(sec_title))
        cells.extend(sec_cells)
    return cells


# ─── MAIN ────────────────────────────────────────────────────────────────────

def reorganize_dsa() -> None:
    print("\n──── 01-dsa/examples/ ────")
    dsa = ROOT / "01-dsa" / "examples"
    dsa_nb = load_nb(dsa / "dsa_complete.ipynb")
    sections = split_at_dividers(dsa_nb)

    # Map section title keywords → concept notebook
    concept_map = {
        "linked_list":            ["Linked", "LRU", "linked list"],
        "stack_queue":            ["Stack", "Queue", "LIFO", "FIFO", "circular"],
        "binary_search_tree":     ["Binary Search Tree", "BST", "AVL", "Balanced", "Tree"],
        "heap_priority_queue":    ["Heap", "heap", "Priority", "heapq"],
        "hash_table":             ["Hash", "hash_table", "Two Sum", "hashing"],
        "trie":                   ["Trie", "trie", "Prefix", "autocomplete"],
        "bit_manipulation":       ["Bit", "bit_manipulation"],
        "sorting_searching":      ["Sorting", "Sort", "Binary Search", "Search"],
        "graphs":                 ["Graph", "BFS", "DFS", "Dijkstra", "Topological", "MST", "cycle"],
        "recursion_dp":           ["Recursion", "DP", "Dynamic", "Greedy", "Backtracking",
                                   "memoiz", "tabulation", "knapsack"],
    }

    buckets: dict[str, list[tuple[str, list[dict]]]] = {k: [] for k in concept_map}
    extras: list[tuple[str, list[dict]]] = []

    for title, cells in sections:
        placed = False
        for concept, keywords in concept_map.items():
            if any(kw.lower() in title.lower() for kw in keywords):
                buckets[concept].append((title, cells))
                placed = True
                break
        if not placed:
            extras.append((title, cells))

    titles_subs = {
        "linked_list":         ("Linked List", "Singly · Doubly · LRU Cache · Cycle Detection · Real-World"),
        "stack_queue":         ("Stack & Queue", "LIFO · FIFO · Monotonic Stack · Deque · Real-World"),
        "binary_search_tree":  ("Binary Search Tree & AVL", "BST · Self-Balancing · 4 Traversals · Real-World"),
        "heap_priority_queue": ("Heap & Priority Queue", "Min/Max Heap · heapq · Top-K · Lazy Deletion · Real-World"),
        "hash_table":          ("Hash Table", "From Scratch · Collision Resolution · Python dict/set · Real-World"),
        "trie":                ("Trie (Prefix Tree)", "Insert · Search · Autocomplete · Delete · Real-World"),
        "bit_manipulation":    ("Bit Manipulation", "All Operators · XOR Tricks · Subset Masks · Real-World"),
        "sorting_searching":   ("Sorting & Binary Search", "All Sorts · Stability · Timsort · bisect · Real-World"),
        "graphs":              ("Graph Algorithms", "BFS/DFS · Dijkstra · Topo Sort · Cycle Detection · Real-World"),
        "recursion_dp":        ("Recursion & Dynamic Programming", "Memoisation · Tabulation · Greedy · Backtracking · Real-World"),
    }

    for concept, sec_list in buckets.items():
        if not sec_list:
            continue
        title, sub = titles_subs[concept]
        cells = build_notebook(title, sub, sec_list)
        write_nb(cells, dsa / f"{concept}.ipynb")

    # Extras (real-world scenarios) go into a summary notebook
    if extras:
        cells = build_notebook("DSA — Production Insights",
                                "Real-World Problem Statements · Before/After · Framework References",
                                extras)
        write_nb(cells, dsa / "dsa_production_insights.ipynb")

    # Delete the big consolidated notebook
    (dsa / "dsa_complete.ipynb").unlink(missing_ok=True)
    print("  🗑  Deleted: dsa_complete.ipynb")


def reorganize_python() -> None:
    print("\n──── 00-python-foundations/ ────")
    pf = ROOT / "00-python-foundations"

    _concept_map_py = {
        "py_types_collections": (
            "Python Types & Collections",
            "Variables · Mutability · Aliasing · is vs == · list/tuple/set/dict · collections module · Real-World",
            ["python_core.ipynb"],
        ),
        "py_functions_closures": (
            "Functions, Closures & Decorators",
            "Parameters · LEGB scope · Closures · Late-binding · Comprehensions · functools · Real-World",
            [],  # subset of python_core — we extract from it
        ),
        "py_oop": (
            "Object-Oriented Programming",
            "4 Pillars · MRO · Protocols · Dataclasses · classmethod/staticmethod · Real-World",
            ["python_oop.ipynb"],
        ),
        "py_iterators_generators": (
            "Iterators, Generators & Context Managers",
            "Iterator protocol · yield · yield from · send() · itertools · @contextmanager · Real-World",
            ["python_iterators_generators.ipynb"],
        ),
        "py_advanced": (
            "Advanced Python Internals",
            "Dunder methods · Descriptors · __slots__ · Metaclasses · Typing · Memory model · Real-World",
            ["python_advanced.ipynb"],
        ),
    }

    # python_core.ipynb covers types, collections AND functions/closures
    # Split it: sections mentioning functions/closures → py_functions_closures
    #           everything else → py_types_collections
    core_nb = load_nb(pf / "python_core.ipynb")
    core_sections = split_at_dividers(core_nb)

    fn_keywords  = ["Function", "Closure", "Lambda", "Decorator", "Comprehension",
                    "LEGB", "nonlocal", "global", "walrus", "functools"]
    _type_keywords = ["Variable", "Type", "Collection", "Operator", "truthiness",
                     "list", "dict", "set", "tuple", "Built-in", "Loop", "Control",
                     "Exception", "File", "Scenario"]

    type_sections: list[tuple[str, list[dict]]] = []
    fn_sections:   list[tuple[str, list[dict]]] = []

    for title, cells in core_sections:
        if any(kw.lower() in title.lower() for kw in fn_keywords):
            fn_sections.append((title, cells))
        else:
            type_sections.append((title, cells))

    # py_types_collections
    cells = build_notebook("Python Types & Collections",
                            "Variables · Mutability · Aliasing · is vs == · list/tuple/set/dict · "
                            "collections · Real-World Production Scenarios",
                            type_sections)
    write_nb(cells, pf / "py_types_collections.ipynb")

    # py_functions_closures (from core + supplement with data_structures comprehensions)
    cells = build_notebook("Python Functions, Closures & Decorators",
                            "Parameters · LEGB · Closures · Late-binding · Comprehensions · "
                            "functools · Real-World Production Scenarios",
                            fn_sections)
    write_nb(cells, pf / "py_functions_closures.ipynb")

    # py_oop — directly from python_oop.ipynb (already the right scope)
    oop_nb = load_nb(pf / "python_oop.ipynb")
    oop_sections = split_at_dividers(oop_nb)
    cells = build_notebook("Object-Oriented Programming",
                            "4 Pillars · MRO · Protocols vs ABC · Dataclasses · "
                            "classmethod/staticmethod · Descriptors · Real-World",
                            oop_sections)
    write_nb(cells, pf / "py_oop.ipynb")

    # py_iterators_generators — from python_iterators_generators.ipynb
    ig_nb = load_nb(pf / "python_iterators_generators.ipynb")
    ig_sections = split_at_dividers(ig_nb)
    cells = build_notebook("Iterators, Generators & Context Managers",
                            "Iterator protocol · yield · yield from · send() · "
                            "itertools (complete) · @contextmanager · ExitStack · Real-World",
                            ig_sections)
    write_nb(cells, pf / "py_iterators_generators.ipynb")

    # py_advanced — from python_advanced.ipynb
    adv_nb = load_nb(pf / "python_advanced.ipynb")
    adv_sections = split_at_dividers(adv_nb)
    cells = build_notebook("Advanced Python Internals",
                            "All Dunder Methods · Descriptor Protocol · __slots__ · "
                            "Metaclasses · Typing & Protocols · CPython Memory Model · Real-World",
                            adv_sections)
    write_nb(cells, pf / "py_advanced.ipynb")

    # python_data_structures — stays as is (already well-scoped)
    print("  →  python_data_structures.ipynb  (kept as-is)")

    # Delete the old consolidated notebooks
    for name in ["python_core.ipynb", "python_oop.ipynb",
                 "python_iterators_generators.ipynb", "python_advanced.ipynb"]:
        p = pf / name
        if p.exists() and name not in {"py_oop.ipynb", "py_iterators_generators.ipynb", "py_advanced.ipynb"}:
            p.unlink()
            print(f"  🗑  Deleted: {name}")


def reorganize_design_patterns() -> None:
    print("\n──── 03-design-patterns/examples/ ────")
    dp = ROOT / "03-design-patterns" / "examples"
    dp_nb = load_nb(dp / "design_patterns_complete.ipynb")
    sections = split_at_dividers(dp_nb)

    cat_map = {
        "creational_patterns": (
            "Creational Design Patterns",
            "Factory Method · Abstract Factory · Builder · Prototype · Singleton · Real-World Scenarios",
            ["Factory", "Abstract Factory", "Builder", "Prototype", "Singleton", "Creational"],
        ),
        "structural_patterns": (
            "Structural Design Patterns",
            "Adapter · Bridge · Composite · Decorator · Facade · Flyweight · Proxy · Real-World Scenarios",
            ["Adapter", "Bridge", "Composite", "Decorator", "Facade", "Flyweight", "Proxy", "Structural"],
        ),
        "behavioral_patterns": (
            "Behavioral Design Patterns",
            "Strategy · Observer · Command · Chain · State · Template · Visitor · Memento · Iterator · Mediator",
            ["Strategy", "Observer", "Command", "Chain", "State", "Template", "Visitor",
             "Memento", "Iterator", "Mediator", "Interpreter", "Behavioral"],
        ),
        "resilience_patterns": (
            "Production & Resilience Patterns",
            "Circuit Breaker · Retry + Backoff + Jitter · Anti-patterns · Interview Bank",
            ["Circuit", "Retry", "Backoff", "Anti-pattern", "Over-engineering",
             "Interview", "Production", "Resilience", "Pattern Mindset"],
        ),
    }

    buckets: dict[str, list[tuple[str, list[dict]]]] = {k: [] for k in cat_map}

    for title, cells in sections:
        placed = False
        for concept, (_, _, keywords) in cat_map.items():
            if any(kw.lower() in title.lower() for kw in keywords):
                buckets[concept].append((title, cells))
                placed = True
                break
        if not placed:
            buckets["resilience_patterns"].append((title, cells))  # catch-all

    for concept, (title, sub, _) in cat_map.items():
        sec_list = buckets[concept]
        if not sec_list:
            continue
        cells = build_notebook(title, sub, sec_list)
        write_nb(cells, dp / f"{concept}.ipynb")

    (dp / "design_patterns_complete.ipynb").unlink(missing_ok=True)
    print("  🗑  Deleted: design_patterns_complete.ipynb")


def print_final_inventory() -> None:
    print("\n" + "="*64)
    print("FINAL NOTEBOOK INVENTORY")
    print("="*64)
    all_nbs = sorted(ROOT.rglob("*.ipynb"))
    for nb in all_nbs:
        if "checkpoints" not in str(nb):
            rel  = str(nb).replace(str(ROOT) + "\\", "").replace("\\", "/")
            info = f"{nb.stat().st_size//1024}KB"
            cells = len(json.loads(nb.read_text(encoding="utf-8"))["cells"])
            print(f"  {rel:65s} {cells:3d} cells  {info}")


def main() -> None:
    print("="*64)
    print("NOTEBOOK REORGANIZATION — Concept-Level Granularity")
    print("="*64)
    reorganize_dsa()
    reorganize_python()
    reorganize_design_patterns()
    print_final_inventory()


if __name__ == "__main__":
    main()
