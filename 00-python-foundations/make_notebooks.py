#!/usr/bin/env python3
"""
make_notebooks.py
=================
Converts every .py file in 00-python-foundations/ into a matching .ipynb
Jupyter notebook.

Parsing rules
─────────────
  ① Module docstring        → Markdown title cell
  ② Import / setup block    → single "Setup" code cell
  ③ Lines matching          → new Markdown section header cell
     `# ═══...` or `# ───...`
  ④ Consecutive top-level   → Markdown cell (stripped of leading `# `)
     comment lines
  ⑤ sep("TITLE") call       → Markdown `## TITLE` cell (new section)
  ⑥ def/class blocks,       → Code cell
     assert/print stmts

Run from the project root:
    python 00-python-foundations/make_notebooks.py
"""
from __future__ import annotations
import json, re, uuid
from pathlib import Path

HERE   = Path(__file__).parent
OUTPUT = HERE  # notebooks written alongside the .py files


# ─── helpers ────────────────────────────────────────────────────────────────

def _id() -> str:
    return uuid.uuid4().hex[:12]


def _src(text: str) -> list[str]:
    """Convert a plain string to notebook source array (newlines preserved)."""
    lines = text.split("\n")
    return [l + "\n" if i < len(lines) - 1 else l
            for i, l in enumerate(lines)]


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": _src(text.strip())}


def code_cell(text: str) -> dict:
    return {"cell_type": "code", "id": _id(), "execution_count": None,
            "metadata": {"collapsed": False}, "outputs": [],
            "source": _src(text.strip())}


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


# ─── tokeniser ──────────────────────────────────────────────────────────────

_SEP_RE   = re.compile(r"^#\s*[═─]{8,}")        # ══════ or ──────
_SEP_LIT  = re.compile(r"^# [═─]{8,}")
_COMMENT  = re.compile(r"^(\s*)#(.*)")           # any comment line
_SEP_CALL = re.compile(r"""sep\(["'](.+?)["']\)""")  # sep("TITLE")
_DOCSTR_S = re.compile(r'^\s*"""')


def _strip_comment(line: str) -> str:
    """Remove the leading `# ` or `#` from a comment line."""
    m = _COMMENT.match(line)
    if not m:
        return line
    body = m.group(2)
    return body[1:] if body.startswith(" ") else body


def _is_top_comment(line: str) -> bool:
    """Top-level (non-indented) comment line."""
    return bool(re.match(r"^#", line))


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def tokenise(text: str) -> list[tuple[str, str]]:
    """
    Returns a list of (kind, content) tokens:
      "docstring"  – the module docstring text
      "sep"        – section separator (content = title extracted from comment)
      "comment"    – block of top-level comment lines
      "code"       – block of code lines
    """
    lines = text.split("\n")
    tokens: list[tuple[str, str]] = []

    # ── 1. Module docstring ──────────────────────────────────────────────────
    i = 0
    while i < len(lines) and (_is_blank(lines[i]) or
                               lines[i].startswith("#!")):
        i += 1

    doc_lines: list[str] = []
    if i < len(lines) and lines[i].lstrip().startswith('"""'):
        if lines[i].count('"""') >= 2:          # single-line
            inner = lines[i].strip().strip('"')
            doc_lines.append(inner)
            i += 1
        else:
            i += 1                               # skip opening """
            while i < len(lines) and '"""' not in lines[i]:
                doc_lines.append(lines[i])
                i += 1
            i += 1                               # skip closing """

    if doc_lines:
        tokens.append(("docstring", "\n".join(doc_lines)))

    # ── 2. Rest of file ──────────────────────────────────────────────────────
    comment_buf: list[str] = []
    code_buf:    list[str] = []

    def flush_comment():
        if comment_buf:
            tokens.append(("comment", "\n".join(comment_buf)))
            comment_buf.clear()

    def flush_code():
        content = "\n".join(code_buf).strip()
        if content:
            tokens.append(("code", content))
        code_buf.clear()

    while i < len(lines):
        line = lines[i]

        # ── section separator ─────────────────────────────────────────
        if _SEP_RE.match(line):
            flush_comment()
            flush_code()
            # collect the title block (next few comment lines)
            title_parts: list[str] = []
            i += 1
            while i < len(lines) and _is_top_comment(lines[i]) and \
                    not _SEP_RE.match(lines[i]):
                title_parts.append(_strip_comment(lines[i]))
                i += 1
            if _SEP_RE.match(lines[i] if i < len(lines) else ""):
                i += 1  # skip closing separator
            tokens.append(("sep", "\n".join(title_parts).strip()))
            continue

        # ── sep("TITLE") call in code → section header ────────────────
        m = _SEP_CALL.search(line)
        if m and not line.lstrip().startswith("#"):
            flush_comment()
            flush_code()
            tokens.append(("sep", m.group(1)))
            i += 1
            continue

        # ── top-level comment (not separator) ─────────────────────────
        if _is_top_comment(line):
            if code_buf:
                flush_code()
            comment_buf.append(_strip_comment(line))
            i += 1
            continue

        # ── blank line ─────────────────────────────────────────────────
        if _is_blank(line):
            if comment_buf:
                flush_comment()
            code_buf.append(line)
            i += 1
            continue

        # ── regular code ───────────────────────────────────────────────
        if comment_buf:
            flush_comment()
        code_buf.append(line)
        i += 1

    flush_comment()
    flush_code()
    return tokens


# ─── notebook builder ───────────────────────────────────────────────────────

def _comment_to_md(text: str) -> str:
    """
    Improve plain comment text as Markdown:
      • Lines that look like headings (ALL-CAPS) → bold
      • Lines starting with 'GOTCHA' → ⚠️ Warning block
      • Lines starting with 'Mental model' → 💡 callout
      • Indented lines → remain as-is (often sub-bullets)
    """
    out: list[str] = []
    for line in text.split("\n"):
        # GOTCHA / WARNING
        if re.match(r"GOTCHA|WARNING|⚠", line, re.I):
            out.append(f"> ⚠️ **{line}**")
        # Mental model / Key insight
        elif re.match(r"Mental model|Key insight|Use Case", line, re.I):
            out.append(f"> 💡 **{line}**")
        # Fix patterns
        elif re.match(r"FIX:|FIX\s|✓|✗", line):
            out.append(line)
        # Lines that look like table rows (contain │ or many ─)
        elif "─" in line or "│" in line:
            out.append(f"`{line}`")
        # Separator lines (long dashes) → HR
        elif re.match(r"─{4,}|═{4,}", line.strip()):
            out.append("---")
        else:
            out.append(line)
    return "\n".join(out)


def tokens_to_cells(tokens: list[tuple[str, str]], title: str) -> list[dict]:
    cells: list[dict] = []

    # Always start with a title cell
    cells.append(md_cell(f"# {title}\n\n*Run each cell with **Shift+Enter***"))

    for kind, content in tokens:
        if kind == "docstring":
            # Use the docstring as a rich intro markdown cell
            cells.append(md_cell(content))

        elif kind == "sep":
            if content.strip():
                cells.append(md_cell(f"## {content.strip()}"))

        elif kind == "comment":
            md = _comment_to_md(content)
            if md.strip():
                cells.append(md_cell(md))

        elif kind == "code":
            if content.strip():
                cells.append(code_cell(content))

    return cells


# ─── main ───────────────────────────────────────────────────────────────────

def convert(py_path: Path) -> Path:
    text  = py_path.read_text(encoding="utf-8")
    title = py_path.stem.replace("_", " ").title()
    toks  = tokenise(text)
    cells = tokens_to_cells(toks, title)
    nb    = make_nb(cells)

    out = OUTPUT / py_path.with_suffix(".ipynb").name
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    py_files = sorted(HERE.glob("*.py"))
    skip = {"make_notebooks.py"}  # don't convert the converter itself
    converted = []
    for f in py_files:
        if f.name in skip:
            continue
        out = convert(f)
        cells = sum(1 for _ in json.loads(out.read_text(encoding="utf-8"))["cells"])
        print(f"  ✓  {f.name:50s} → {out.name}  ({cells} cells)")
        converted.append(out)
    print(f"\nGenerated {len(converted)} notebooks in {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
