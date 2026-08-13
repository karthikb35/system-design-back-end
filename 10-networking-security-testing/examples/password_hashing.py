"""
10 — Security Deep Dive: Password Hashing Done Right
===================================================

Runnable companion to PDF Book VII, Chapter "Storing Secrets & Credentials".

How you store a password is a top cause of catastrophic breaches.

    JUNIOR ANTI-PATTERN  ->  store plaintext, or a fast unsalted hash (md5/sha256).
                            A leaked table is cracked in minutes with rainbow
                            tables / GPU brute force; identical passwords collide.
    SENIOR REFACTOR      ->  a SALTED, SLOW key-derivation function (PBKDF2 here;
                            bcrypt/scrypt/argon2 in production) + CONSTANT-TIME
                            comparison on verify.

Uses only hashlib/hmac/secrets so it runs anywhere.

Run:  python password_hashing.py
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ROUNDS = 200_000          # deliberately slow: ~expensive per guess


def hash_password(password: str, *, rounds: int = PBKDF2_ROUNDS) -> str:
    """Return 'algo$rounds$salt$hash' — the salt is stored WITH the hash."""
    salt = secrets.token_bytes(16)                      # unique random salt per user
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Recompute with the stored salt/rounds and compare in constant time."""
    try:
        algo, rounds_s, salt_hex, hash_hex = stored.split("$")
        assert algo == "pbkdf2_sha256"
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AssertionError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    # constant-time: never short-circuit on the first differing byte
    return hmac.compare_digest(dk, bytes.fromhex(hash_hex))


def demo() -> None:
    stored = hash_password("correct horse battery staple")
    print("stored record:", stored[:56], "...")

    # The right password verifies; the wrong one does not.
    assert verify_password("correct horse battery staple", stored) is True
    assert verify_password("wrong password", stored) is False
    print("correct password accepted, wrong password rejected")

    # Salting: the SAME password hashes DIFFERENTLY for two users, so a leaked
    # table doesn't reveal that two users share a password (defeats rainbow tables).
    a = hash_password("hunter2")
    b = hash_password("hunter2")
    assert a != b
    assert a.split("$")[2] != b.split("$")[2]           # different salts
    assert verify_password("hunter2", a) and verify_password("hunter2", b)
    print("same password -> different stored hashes (unique salts)")

    # A tampered/garbage record fails closed rather than crashing.
    assert verify_password("anything", "not-a-valid-record") is False
    print("malformed stored record rejected safely")

    # The stored value never contains the plaintext.
    assert "correct horse" not in stored
    print("plaintext never stored")


def main() -> None:
    print("=" * 68)
    print("Password hashing: salted, slow PBKDF2 + constant-time verify")
    print("=" * 68)
    demo()
    print("\nAll password-hashing demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
