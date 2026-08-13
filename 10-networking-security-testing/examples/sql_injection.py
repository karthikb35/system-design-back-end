"""
10 — Security Deep Dive: SQL Injection vs Parameterized Queries
==============================================================

Runnable companion to PDF Book VII, Chapter "The OWASP Top 10".

SQL injection is #1 in the "Injection" class of the OWASP Top 10. The cause is
always the same: building a query by STRING CONCATENATION with untrusted input,
so the input can change the query's STRUCTURE.

    JUNIOR ANTI-PATTERN  ->  f"SELECT ... WHERE name = '{user_input}'"
                            input  ' OR '1'='1  -> returns every row (auth bypass)
                            input  '; DROP ...   -> executes a second statement
    SENIOR REFACTOR      ->  parameterized query: the driver sends SQL and DATA
                            separately, so input is ALWAYS data, never code.

We model a tiny SQL engine so the injection is visible without a real database.

Run:  python sql_injection.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MiniDB:
    """A toy 'users' table + a deliberately naive query interpreter."""

    rows: list[dict]

    # ---- ❌ VULNERABLE: interprets a concatenated query string -----------
    def unsafe_query(self, raw_sql: str) -> list[dict]:
        # Supports: SELECT * FROM users WHERE name = '<value>'
        # ...and the injection classics ( OR '1'='1 ), because it parses the
        # STRING the same way a real engine parses submitted SQL.
        if "or '1'='1'" in raw_sql.lower() or "or 1=1" in raw_sql.lower():
            return list(self.rows)                      # predicate always true
        m = re.search(r"name\s*=\s*'([^']*)'", raw_sql, re.IGNORECASE)
        if not m:
            return []
        wanted = m.group(1)
        return [r for r in self.rows if r["name"] == wanted]

    # ---- ✅ SAFE: SQL and parameters are separate; input is only data ----
    def safe_query(self, sql_template: str, params: tuple) -> list[dict]:
        assert sql_template.count("?") == len(params), "param count mismatch"
        # The engine binds params as DATA — they can never alter the structure.
        wanted = params[0]
        return [r for r in self.rows if r["name"] == wanted]


def build_unsafe(user_input: str) -> str:
    # The footgun: interpolating untrusted input straight into SQL.
    return f"SELECT * FROM users WHERE name = '{user_input}'"


def demo() -> None:
    db = MiniDB(rows=[
        {"id": 1, "name": "alice", "role": "user"},
        {"id": 2, "name": "bob", "role": "user"},
        {"id": 3, "name": "root", "role": "admin"},
    ])

    # Normal lookup works either way.
    assert db.unsafe_query(build_unsafe("alice"))[0]["id"] == 1
    assert db.safe_query("SELECT * FROM users WHERE name = ?", ("alice",))[0]["id"] == 1
    print("normal lookup returns exactly one row")

    # ❌ INJECTION: the classic auth-bypass payload returns EVERY row.
    payload = "' OR '1'='1"
    leaked = db.unsafe_query(build_unsafe(payload))
    assert len(leaked) == 3                              # whole table exfiltrated
    print(f"injection via unsafe_query leaked all {len(leaked)} rows (auth bypass!)")

    # ✅ The SAME payload through a parameterized query matches NOTHING, because
    #    it is treated as a literal name to look up, not as SQL.
    safe = db.safe_query("SELECT * FROM users WHERE name = ?", (payload,))
    assert safe == []
    print("same payload via parameterized query -> 0 rows (treated as data)")

    # Parameterization also validates arity, catching template/param mismatches.
    try:
        db.safe_query("SELECT * FROM users WHERE name = ? AND role = ?", ("alice",))
        raise AssertionError("should reject param count mismatch")
    except AssertionError as exc:
        if "param count" not in str(exc):
            raise
        print("parameter arity checked")


def main() -> None:
    print("=" * 68)
    print("SQL injection vs parameterized queries")
    print("=" * 68)
    demo()
    print("\nAll SQL-injection demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
