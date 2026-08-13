"""
05 — FastAPI Advanced Deep Dive: Offset vs Cursor (Keyset) Pagination
====================================================================

Runnable companion to PDF Book VI, Chapter "API Design at Scale".

THE PROBLEM: `LIMIT ? OFFSET ?` pagination gets SLOWER the deeper you page
(the DB must scan and discard all skipped rows) and can SKIP/DUPLICATE rows
when data is inserted between page requests.

    JUNIOR          ->  OFFSET pagination: page 10000 scans ~200k rows to skip
    SENIOR          ->  KEYSET (cursor) pagination: WHERE id > last_seen ORDER
                        BY id LIMIT n  -> constant work per page, stable results

We model a sorted table and COUNT the rows the DB must touch, so the pathology
is visible without a real database.

Run:  python pagination.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    id: int
    title: str


class FakeTable:
    """A table sorted by id. `.scanned` counts rows the engine had to touch."""

    def __init__(self, n: int) -> None:
        self._rows = [Row(i, f"item-{i}") for i in range(1, n + 1)]
        self.scanned = 0

    def reset(self) -> None:
        self.scanned = 0

    # ---- OFFSET pagination: must walk from the start every time ----------
    def page_offset(self, limit: int, offset: int) -> list[Row]:
        out: list[Row] = []
        for row in self._rows:              # engine scans from the beginning
            self.scanned += 1
            if self.scanned <= offset:      # ...discarding `offset` rows
                continue
            out.append(row)
            if len(out) == limit:
                break
        return out

    # ---- KEYSET pagination: jump to the cursor via the index -------------
    def page_keyset(self, limit: int, after_id: int = 0) -> list[Row]:
        # A real DB uses the B-tree index to seek straight to `after_id`.
        lo, hi = 0, len(self._rows)
        while lo < hi:                      # binary seek == index lookup
            mid = (lo + hi) // 2
            if self._rows[mid].id <= after_id:
                lo = mid + 1
            else:
                hi = mid
        out = self._rows[lo:lo + limit]
        self.scanned += len(out)            # only touches the rows returned
        return out


def demo() -> None:
    table = FakeTable(200_000)
    limit = 20

    # Deep page via OFFSET — scans everything up to the offset.
    table.reset()
    deep_offset = table.page_offset(limit, offset=180_000)
    offset_scanned = table.scanned

    # Same deep page via KEYSET — cursor is the id just before the page.
    table.reset()
    deep_keyset = table.page_keyset(limit, after_id=180_000)
    keyset_scanned = table.scanned

    print(f"OFFSET deep page: scanned {offset_scanned:,} rows for {limit} results")
    print(f"KEYSET deep page: scanned {keyset_scanned:,} rows for {limit} results")
    print(f"keyset is ~{offset_scanned // max(keyset_scanned,1):,}x cheaper here")

    # Both return the same window of data...
    assert [r.id for r in deep_offset] == [r.id for r in deep_keyset]
    # ...but keyset only touched the rows it returned.
    assert keyset_scanned == limit
    assert offset_scanned > 180_000
    assert offset_scanned > keyset_scanned * 1000

    # Full forward walk with keyset stays O(limit) per page regardless of depth.
    cursor, pages = 0, 0
    while True:
        table.reset()
        rows = table.page_keyset(limit, after_id=cursor)
        if not rows:
            break
        assert table.scanned <= limit       # constant work every page
        cursor = rows[-1].id
        pages += 1
    assert pages == 200_000 // limit


def main() -> None:
    print("=" * 68)
    print("OFFSET vs KEYSET (cursor) pagination")
    print("=" * 68)
    demo()
    print("\nAll pagination demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
