#!/usr/bin/env python3
"""Render a study-guide HTML book to PDF with headless Chromium (Playwright).

WHY Chromium and not weasyprint/pandoc: the books in this folder are styled with
`@page` rules, CSS gradients, `print-color-adjust:exact`, custom fonts and color
emoji (see ``architects-path.css``). Chromium's print pipeline is the only engine
that reproduces that layout faithfully — it is exactly what "Print to PDF" uses.

Usage:
    python render_pdf.py <input.html> <output.pdf>

Local (Windows/macOS/Linux) one-time setup:
    pip install playwright
    python -m playwright install chromium

The CI workflow (.github/workflows/docs-pdf.yml) calls this once per book and only
for books whose HTML (or the shared CSS) changed; unchanged books are carried over
from the previous release instead of being re-rendered.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def render(html_path: str, pdf_path: str) -> None:
    src = Path(html_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"HTML source not found: {src}")

    out = Path(pdf_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # Load from the file:// URI so the relative <link> to the shared CSS
        # resolves exactly as it does when opened in a browser.
        page.goto(src.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(out),
            # Honour the book's own `@page { size: A4 }` rule.
            prefer_css_page_size=True,
            # Keep the dark cover gradients and colored callout boxes.
            print_background=True,
        )
        browser.close()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: render_pdf.py <input.html> <output.pdf>", file=sys.stderr)
        return 2
    render(argv[1], argv[2])
    print(f"wrote {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
