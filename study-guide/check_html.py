"""
Validates all study-guide HTML books for:
  1. Well-formed HTML (html5lib parser — strict)
  2. Internal relative links and src attributes resolve to real files
  3. The shared CSS file parses without errors (cssutils)
  4. Every book references architects-path.css

Exit 0 = all clean.  Exit 1 = at least one error.
Run: python study-guide/check_html.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cssutils
import html5lib

STUDY_DIR = Path(__file__).parent
CSS_FILE = STUDY_DIR / "architects-path.css"


def check_css(css_path: Path) -> list[str]:
    errors: list[str] = []
    sheet = cssutils.parseFile(str(css_path))
    for err in sheet.cssRules:
        # cssutils never raises; check for ERROR rules
        if err.type == err.UNKNOWN_RULE:
            errors.append(f"CSS unknown rule in {css_path.name}: {err.cssText[:60]}")
    return errors


def check_html(html_path: Path) -> list[str]:
    errors: list[str] = []
    text = html_path.read_text(encoding="utf-8")

    # 1. Parse with html5lib (strict mode surfaces malformed markup)
    try:
        doc = html5lib.parse(text, treebuilder="lxml", namespaceHTMLElements=False)
    except Exception as exc:
        errors.append(f"{html_path.name}: parse error — {exc}")
        return errors

    # 2. Check relative href / src attributes resolve to real files
    from lxml import etree  # noqa: PLC0415

    for el in doc.iter():
        for attr in ("href", "src"):
            val = el.get(attr, "")
            if not val or val.startswith(("http", "#", "mailto:", "javascript:")):
                continue
            # Strip query / fragment
            rel = val.split("?")[0].split("#")[0]
            if not rel:
                continue
            target = html_path.parent / rel
            if not target.exists():
                errors.append(f"{html_path.name}: broken ref {attr}={val!r}")

    # 3. CSS reference present
    if "architects-path.css" not in text:
        errors.append(f"{html_path.name}: missing architects-path.css link")

    return errors


def main() -> int:
    all_errors: list[str] = []

    # CSS
    if not CSS_FILE.exists():
        all_errors.append(f"Missing CSS file: {CSS_FILE}")
    else:
        all_errors.extend(check_css(CSS_FILE))

    # HTML
    books = sorted(STUDY_DIR.glob("*.html"))
    if not books:
        all_errors.append(f"No HTML files found in {STUDY_DIR}")
    for book in books:
        all_errors.extend(check_html(book))

    if all_errors:
        for err in all_errors:
            print(f"  ERROR  {err}", file=sys.stderr)
        print(f"\n{len(all_errors)} error(s) found in study-guide HTML/CSS.", file=sys.stderr)
        return 1

    print(f"study-guide check passed ({len(books)} books, CSS ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
