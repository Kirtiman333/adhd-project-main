"""
Tests for password hashing (src/common/security.py).

    pytest tests/test_security.py
    python tests/test_security.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.security import (  # noqa: E402
    hash_password,
    verify_password,
    is_hashed,
    needs_rehash,
)


def test_hash_is_not_plaintext_and_is_salted():
    h = hash_password("hunter2")
    assert "hunter2" not in h
    assert is_hashed(h)
    # Same password hashed twice -> different salts -> different strings.
    assert hash_password("hunter2") != h


def test_verify_correct_and_incorrect():
    h = hash_password("correct horse")
    assert verify_password("correct horse", h) is True
    assert verify_password("wrong", h) is False
    assert verify_password("", h) is False


def test_legacy_plaintext_still_verifies():
    # Old profiles stored raw passwords; verify must still accept them.
    assert verify_password("oldpass", "oldpass") is True
    assert verify_password("nope", "oldpass") is False
    assert is_hashed("oldpass") is False


def test_needs_rehash():
    assert needs_rehash("plaintextvalue") is True       # legacy
    assert needs_rehash(hash_password("x")) is False     # current params
    assert needs_rehash("pbkdf2_sha256$1000$aa$bb") is True  # too-few iterations


def test_verify_handles_garbage():
    assert verify_password("x", None) is False
    assert verify_password("x", "pbkdf2_sha256$notanint$zz$zz") is False


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
