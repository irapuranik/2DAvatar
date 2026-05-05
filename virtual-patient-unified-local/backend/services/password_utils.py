"""Bcrypt password hashing without passlib (passlib 1.7.x breaks on bcrypt 5.x)."""
from __future__ import annotations

import bcrypt

# Bcrypt ignores input beyond 72 bytes; match that so verify matches prior passlib hashes.
_MAX = 72


def hash_password(raw: str) -> str:
    b = raw.encode("utf-8")
    if len(b) > _MAX:
        b = b[:_MAX]
    return bcrypt.hashpw(b, bcrypt.gensalt()).decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        b = raw.encode("utf-8")
        if len(b) > _MAX:
            b = b[:_MAX]
        return bcrypt.checkpw(b, hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False
