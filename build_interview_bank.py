#!/usr/bin/env python3
"""
build_interview_bank.py
=======================
1. Reads every interview_questions.md file (00-10 folders).
2. Appends a structured "Interview Questions" section to the matching notebook(s).
3. Creates one master interview_bank.ipynb with ALL questions.

Run: python build_interview_bank.py
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).parent

FOLDER_TO_NOTEBOOKS = {
    "00-python-foundations": [
        "00-python-foundations/py_types_collections.ipynb",
        "00-python-foundations/py_functions_closures.ipynb",
        "00-python-foundations/py_oop.ipynb",
        "00-python-foundations/py_iterators_generators.ipynb",
        "00-python-foundations/py_advanced.ipynb",
    ],
    "01-dsa": ["01-dsa/examples/dsa_complete_iq.ipynb"],  # new file
    "02-solid": ["02-solid/examples/solid_complete.ipynb"],
    "03-design-patterns": ["03-design-patterns/examples/resilience_patterns.ipynb"],
    "04-system-design": [],   # no notebook yet
    "05-fastapi-advanced": [],
    "06-elk-monitoring": [],
    "07-database-scaling": [],
    "08-event-driven-systems": [],
    "09-concurrency": [],
    "10-networking-security-testing": [],
}

# For modules 04-10, we create standalone IQ notebooks
STANDALONE_IQ_FOLDERS = [
    "04-system-design",
    "05-fastapi-advanced",
    "06-elk-monitoring",
    "07-database-scaling",
    "08-event-driven-systems",
    "09-concurrency",
    "10-networking-security-testing",
]


def nid() -> str:
    return uuid.uuid4().hex[:12]


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "id": nid(), "metadata": {},
            "source": [text.rstrip()]}


def code_cell(text: str) -> dict:
    return {"cell_type": "code", "id": nid(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": [text.rstrip()]}


def make_nb(cells: list[dict]) -> dict:
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)",
                           "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "cells": cells,
    }


def parse_md_to_cells(md_text: str, folder_title: str) -> list[dict]:
    """
    Convert an interview_questions.md into notebook cells.
    Each Q### block → a markdown cell.
    Multiple-choice / answer key / gotchas → styled markdown.
    """
    cells: list[dict] = []
    # Section header
    cells.append(md_cell(f"---\n## 🏆 Interview Questions — {folder_title}\n\n"
                          f"*Model answers included. Say your answer aloud before reading.*"))

    # Split on ### Q headings
    blocks = re.split(r"(?=^### Q)", md_text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Convert markdown headings to notebook markdown
        # Highlight Q headings
        if block.startswith("### Q"):
            # Extract question number and title
            first_line = block.split("\n")[0]
            rest = "\n".join(block.split("\n")[1:])
            # Style the question
            styled = f"### {first_line[4:]}\n\n{rest}"
            cells.append(md_cell(styled))
        elif block.startswith("## Part"):
            # Part headers (multiple-choice etc.)
            cells.append(md_cell(block))
        elif block.startswith("#"):
            cells.append(md_cell(block))
        else:
            if block:
                cells.append(md_cell(block))

    return cells


def read_iq_md(folder: str) -> tuple[str, str]:
    """Returns (title, markdown_content)."""
    md_path = ROOT / folder / "interview_questions.md"
    if not md_path.exists():
        return "", ""
    text = md_path.read_text(encoding="utf-8")
    # Extract title from first heading
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else folder
    return title, text


def append_iq_to_notebook(nb_path_str: str, cells: list[dict]) -> None:
    """Append interview Q cells to an existing notebook."""
    p = ROOT / nb_path_str
    if not p.exists():
        print(f"  SKIP (not found): {nb_path_str}")
        return
    nb = json.loads(p.read_text(encoding="utf-8"))
    # Check if already appended
    existing = " ".join("".join(c.get("source", [])) for c in nb["cells"])
    if "Interview Questions" in existing and "Model answers" in existing:
        print(f"  SKIP (already has IQ): {p.name}")
        return
    nb["cells"].extend(cells)
    p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  ↳  Appended {len(cells)} cells → {p.name}  "
          f"(now {len(nb['cells'])} cells, {p.stat().st_size//1024}KB)")


def create_standalone_iq_notebook(folder: str, title: str, cells: list[dict]) -> None:
    """Create a standalone interview questions notebook."""
    out_dir = ROOT / folder / "examples"
    out_dir.mkdir(exist_ok=True)
    header = [md_cell(f"# 🏆 Interview Questions — {title}\n\n"
                       f"*Deep-dive Q&A for staff/principal-level interviews.*\n\n"
                       f"**How to use:** Say your answer aloud, then read the model answer. "
                       f"If you can't name the failure mode and the trade-off, study the section again.")]
    nb = make_nb(header + cells)
    path = out_dir / "interview_questions.ipynb"
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓  {folder}/examples/interview_questions.ipynb  "
          f"({len(nb['cells'])} cells, {path.stat().st_size//1024}KB)")


def build_master_bank(all_sections: list[tuple[str, list[dict]]]) -> None:
    """Create one master notebook with every question."""
    cells: list[dict] = [
        md_cell(
            "# 🏆 Master Interview Bank — The Architect's Path\n\n"
            "*Every interview question from all 11 modules in one place.*\n\n"
            "**Scope:** Python Foundations · DSA · SOLID · Design Patterns · "
            "System Design · FastAPI · ELK · Database Scaling · "
            "Event-Driven Systems · Concurrency · Networking & Security\n\n"
            "**Format:** 5–6 deep-dive questions per module with full model answers, "
            "a multiple-choice check, and a gotchas checklist."
        )
    ]
    for title, section_cells in all_sections:
        cells.append(md_cell(f"---\n# {title}"))
        cells.extend(section_cells)

    nb = make_nb(cells)
    path = ROOT / "interview_bank.ipynb"
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  ✓  interview_bank.ipynb  "
          f"({len(nb['cells'])} cells, {path.stat().st_size//1024}KB)  ← MASTER BANK")


def main() -> None:
    print("=" * 64)
    print("BUILDING INTERVIEW BANKS")
    print("=" * 64)

    all_sections: list[tuple[str, list[dict]]] = []

    for folder in sorted(FOLDER_TO_NOTEBOOKS.keys()):
        title, md_text = read_iq_md(folder)
        if not md_text:
            continue
        print(f"\n{folder}/")
        iq_cells = parse_md_to_cells(md_text, title)

        # Append to existing notebooks (00-03)
        nb_targets = FOLDER_TO_NOTEBOOKS[folder]
        if nb_targets:
            for nb_path in nb_targets:
                # Only append to the LAST/primary notebook (avoid cluttering all)
                break  # append to first target only
            append_iq_to_notebook(nb_targets[0], iq_cells)

        # Create standalone for modules without notebooks yet (04-10)
        if folder in STANDALONE_IQ_FOLDERS:
            create_standalone_iq_notebook(folder, title, iq_cells)

        all_sections.append((title, iq_cells))

    # For 00-python-foundations: also create a standalone IQ notebook
    title_py, md_py = read_iq_md("00-python-foundations")
    if md_py:
        iq_cells_py = parse_md_to_cells(md_py, title_py)
        path = ROOT / "00-python-foundations" / "interview_questions.ipynb"
        nb = make_nb([md_cell("# 🏆 Interview Questions — Python Foundations\n\n"
                               "*Deep-dive Q&A with model answers.*")] + iq_cells_py)
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓  00-python-foundations/interview_questions.ipynb  "
              f"({len(nb['cells'])} cells)")

    # For 01-dsa: standalone
    title_dsa, md_dsa = read_iq_md("01-dsa")
    if md_dsa:
        iq_cells_dsa = parse_md_to_cells(md_dsa, title_dsa)
        path = ROOT / "01-dsa" / "examples" / "interview_questions.ipynb"
        nb = make_nb([md_cell("# 🏆 Interview Questions — DSA\n\n"
                               "*Deep-dive Q&A with model answers.*")] + iq_cells_dsa)
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓  01-dsa/examples/interview_questions.ipynb  "
              f"({len(nb['cells'])} cells)")

    # Master bank
    print("\nBuilding master interview_bank.ipynb ...")
    build_master_bank(all_sections)

    print("\n" + "=" * 64)
    print("DONE")
    print("=" * 64)
    print("\nWhere to find interview questions:")
    print("  interview_bank.ipynb            ← MASTER: all 11 modules")
    print("  00-python-foundations/interview_questions.ipynb")
    print("  01-dsa/examples/interview_questions.ipynb")
    print("  02-solid/examples/solid_complete.ipynb    (appended)")
    print("  03-design-patterns/examples/resilience_patterns.ipynb  (appended)")
    print("  04-10/examples/interview_questions.ipynb  (standalone per module)")


if __name__ == "__main__":
    main()
