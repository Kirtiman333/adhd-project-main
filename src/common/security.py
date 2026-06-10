"""
Password hashing — standard library only.

Stores credentials as salted PBKDF2-HMAC-SHA256 hashes in a single string:

    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>

verify_password also accepts a non-hashed (plaintext) value and compares it
directly, so plaintext profiles still authenticate; call needs_rehash after a
successful login to upgrade those entries to a real hash transparently.
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str, *, iterations: int = _ITERATIONS) -> str:
    """Return a salted PBKDF2 hash string for `password`."""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def is_hashed(stored: str) -> bool:
    """True if `stored` looks like a value produced by hash_password."""
    return isinstance(stored, str) and stored.startswith(_ALGO + "$") and stored.count("$") == 3


def verify_password(password: str, stored: str) -> bool:
    """Check `password` against a stored hash (or a legacy plaintext value).

    Uses a constant-time comparison in both branches.
    """
    if stored is None:
        return False
    if not is_hashed(stored):
        # Legacy plaintext entry — compare directly so old accounts still log in.
        return hmac.compare_digest(str(password), str(stored))

    try:
        _algo, iter_s, salt_hex, hash_hex = stored.split("$")
        iterations = int(iter_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored: str) -> bool:
    """True if a stored credential should be upgraded (legacy plaintext or weaker params)."""
    if not is_hashed(stored):
        return True
    try:
        _algo, iter_s, _salt, _hash = stored.split("$")
        return int(iter_s) < _ITERATIONS
    except (ValueError, TypeError):
        return True
