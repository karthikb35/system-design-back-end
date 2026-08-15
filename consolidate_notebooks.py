#!/usr/bin/env python3
"""
consolidate_notebooks.py
========================
Merges multiple .ipynb files into ONE notebook per topic.

Consolidation plan
──────────────────
03-design-patterns/examples/
  → design_patterns_complete.ipynb
    (creational + structural + behavioral + patterns_notebook + patterns_real_world)

02-solid/examples/
  → solid_complete.ipynb
    (solid_principles + solid_notebook)

01-dsa/examples/
  → dsa_complete.ipynb
    (data_structures + balanced_trees + heaps + tries + hash_tables +
     bit_manipulation + sorting_searching + recursion_dp_greedy_backtracking + graphs)

00-python-foundations/
  → python_core.ipynb
    (fundamentals + builtins_loops_complete)
  → python_oop_complete.ipynb
    (oop + oop_complete)           -- oop is small intro; oop_complete is the deep dive
  → python_iterators_generators.ipynb
    (iterators_generators_decorators + iterators_generators_context_complete)
  → python_advanced.ipynb
    (advanced_dunder + descriptors_slots_meta + typing_and_memory)
  → python_data_structures.ipynb
    (data_structures_complete — already standalone)

Run from the project root:
    python consolidate_notebooks.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).parent


def load_cells(path: Path) -> list[dict]:
    """Return all cells from a notebook, skipping empty ones."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    return [c for c in nb["cells"] if "".join(c.get("source", [])).strip()]


def divider_cell(title: str) -> dict:
    """Markdown cell that visually separates merged notebooks."""
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:12],
        "metadata": {},
        "source": [f"---\n# {title}\n"]
    }


def make_cell_id(cell: dict) -> dict:
    """Ensure every cell has a unique id (required by nbformat 4.5+)."""
    if not cell.get("id"):
        cell = dict(cell, id=uuid.uuid4().hex[:12])
    else:
        cell = dict(cell, id=uuid.uuid4().hex[:12])  # re-id to avoid collisions
    return cell


def merge(notebooks: list[tuple[str, Path]], output: Path) -> None:
    """
    Merge listed notebooks in order.
    notebooks: [(section_title, path), ...]
    """
    all_cells: list[dict] = []
    for title, path in notebooks:
        if not path.exists():
            print(f"  WARN: {path.name} not found — skipping")
            continue
        cells = load_cells(path)
        if all_cells:  # not the first notebook — add a visual divider
            all_cells.append(make_cell_id(divider_cell(title)))
        all_cells.extend(make_cell_id(c) for c in cells)
        print(f"    + {path.name:55s} ({len(cells)} cells)")

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "cells": all_cells,
    }
    output.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Written: {output.name}  ({len(all_cells)} cells, "
          f"{output.stat().st_size // 1024}KB)")


def delete_sources(notebooks: list[tuple[str, Path]], keep: Path) -> None:
    for _, path in notebooks:
        if path.exists() and path != keep:
            path.unlink()
            print(f"  🗑  Deleted: {path.name}")


def main() -> None:
    print("=" * 64)
    print("NOTEBOOK CONSOLIDATION")
    print("=" * 64)

    # ── 03-design-patterns ────────────────────────────────────────
    dp = ROOT / "03-design-patterns" / "examples"
    print("\n03-design-patterns → design_patterns_complete.ipynb")
    design_notebooks = [
        ("Design Patterns — Introduction & Mindset", dp / "patterns_notebook.ipynb"),
        ("Real-World Scenarios (ShopFlow)", dp / "patterns_real_world.ipynb"),
        ("Creational Patterns — Reference", dp / "creational.ipynb"),
        ("Structural Patterns — Reference", dp / "structural.ipynb"),
        ("Behavioral Patterns — Reference", dp / "behavioral.ipynb"),
    ]
    out_dp = dp / "design_patterns_complete.ipynb"
    merge(design_notebooks, out_dp)
    delete_sources(design_notebooks, keep=out_dp)

    # ── 02-solid ──────────────────────────────────────────────────
    so = ROOT / "02-solid" / "examples"
    print("\n02-solid → solid_complete.ipynb")
    solid_notebooks = [
        ("SOLID — Before/After Reference",  so / "solid_principles.ipynb"),
        ("SOLID — Exhaustive Notebook",     so / "solid_notebook.ipynb"),
    ]
    out_so = so / "solid_complete.ipynb"
    merge(solid_notebooks, out_so)
    delete_sources(solid_notebooks, keep=out_so)

    # ── 01-dsa ────────────────────────────────────────────────────
    dsa = ROOT / "01-dsa" / "examples"
    print("\n01-dsa → dsa_complete.ipynb")
    dsa_notebooks = [
        # Core linear/tree structures first
        ("Data Structures — Linked Lists, LRU, Stack, Queue, BST, Heap",
         dsa / "data_structures.ipynb"),
        ("Balanced Trees — AVL",               dsa / "balanced_trees.ipynb"),
        ("Heaps — Min/Max, heapq, Top-K",       dsa / "heaps.ipynb"),
        ("Tries — Prefix Trees",                dsa / "tries.ipynb"),
        ("Hash Tables — From Scratch",          dsa / "hash_tables.ipynb"),
        ("Bit Manipulation",                    dsa / "bit_manipulation.ipynb"),
        # Algorithms
        ("Sorting & Binary Search",             dsa / "sorting_searching.ipynb"),
        ("Recursion, DP, Greedy, Backtracking", dsa / "recursion_dp_greedy_backtracking.ipynb"),
        ("Graphs — BFS/DFS/Dijkstra/MST",       dsa / "graphs.ipynb"),
    ]
    out_dsa = dsa / "dsa_complete.ipynb"
    merge(dsa_notebooks, out_dsa)
    delete_sources(dsa_notebooks, keep=out_dsa)

    # ── 00-python-foundations ─────────────────────────────────────
    pf = ROOT / "00-python-foundations"
    print("\n00-python-foundations → 4 topic notebooks")

    # Core language
    print("  python_core.ipynb")
    merge([
        ("Python Fundamentals — Types, Flow, Collections", pf / "fundamentals.ipynb"),
        ("Built-ins, Loops & Comprehensions",              pf / "builtins_loops_complete.ipynb"),
    ], pf / "python_core.ipynb")
    for _, p in [("", pf / "fundamentals.ipynb"), ("", pf / "builtins_loops_complete.ipynb")]:
        if p.exists(): p.unlink(); print(f"  🗑  Deleted: {p.name}")

    # OOP
    print("  python_oop.ipynb")
    merge([
        ("OOP — Foundations",         pf / "oop.ipynb"),
        ("OOP — Complete + MRO + DI", pf / "oop_complete.ipynb"),
    ], pf / "python_oop.ipynb")
    for _, p in [("", pf / "oop.ipynb"), ("", pf / "oop_complete.ipynb")]:
        if p.exists(): p.unlink(); print(f"  🗑  Deleted: {p.name}")

    # Iterators & Generators
    print("  python_iterators_generators.ipynb")
    merge([
        ("Iterators & Generators — Introduction",     pf / "iterators_generators_decorators.ipynb"),
        ("Iterators, Generators & Context Managers — Complete",
         pf / "iterators_generators_context_complete.ipynb"),
    ], pf / "python_iterators_generators.ipynb")
    for _, p in [("", pf / "iterators_generators_decorators.ipynb"),
                 ("", pf / "iterators_generators_context_complete.ipynb")]:
        if p.exists(): p.unlink(); print(f"  🗑  Deleted: {p.name}")

    # Advanced internals
    print("  python_advanced.ipynb")
    merge([
        ("Advanced Dunder Methods",          pf / "advanced_dunder.ipynb"),
        ("Descriptors, __slots__, Metaclasses", pf / "descriptors_slots_meta.ipynb"),
        ("Typing, Protocols & Memory Model", pf / "typing_and_memory.ipynb"),
    ], pf / "python_advanced.ipynb")
    for _, p in [("", pf / "advanced_dunder.ipynb"),
                 ("", pf / "descriptors_slots_meta.ipynb"),
                 ("", pf / "typing_and_memory.ipynb")]:
        if p.exists(): p.unlink(); print(f"  🗑  Deleted: {p.name}")

    # Data structures (already standalone — just rename for consistency)
    old = pf / "data_structures_complete.ipynb"
    new = pf / "python_data_structures.ipynb"
    if old.exists():
        old.rename(new)
        print(f"  ✓ Renamed: {old.name} → {new.name}")

    print("\n" + "="*64)
    print("CONSOLIDATION COMPLETE")
    print("="*64)
    print("\nFinal notebooks:")
    for f in sorted(ROOT.rglob("*.ipynb")):
        if "checkpoints" not in str(f):
            rel = str(f).replace(str(ROOT) + "\\", "")
            print(f"  {rel}  [{f.stat().st_size//1024}KB]")


if __name__ == "__main__":
    main()
