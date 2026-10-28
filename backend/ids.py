"""Short, sortable IDs: <prefix>_<10 chars of time><6 random chars>, Crockford base32."""
from __future__ import annotations

import secrets
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _b32(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(out))


def new_id(prefix: str) -> str:
    ms = int(time.time() * 1000)
    return f"{prefix}_{_b32(ms, 10)}{_b32(secrets.randbits(30), 6)}"
