"""Persistent per-user and per-IP limits, with bounded local protection during a DB outage."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from collections import deque
from threading import Lock

from backend import db
from backend.config import get_settings
from backend.errors import ApiError

_lock = Lock()
_recent: dict[str, deque[float]] = {}
_emergency_salt = secrets.token_bytes(32)


def client_ip(request) -> str:
    """The proxy appends the address it saw, so the rightmost X-Forwarded-For entry is the one a client can't write.
    (uvicorn's --forwarded-allow-ips='*' reports the leftmost, which the client controls.)"""
    forwarded = [part.strip() for part in request.headers.get('x-forwarded-for', '').split(',') if part.strip()]
    if forwarded:
        return forwarded[-1]
    return request.client.host if request.client else 'unknown'


def enforce(anon_id: str, ip: str) -> None:
    salt = os.getenv('IDENTIFIER_SALT', '').encode() or _emergency_salt
    key = hmac.new(salt, ip.encode(), hashlib.sha256).hexdigest()
    buckets = [('user:' + anon_id, 30), ('ip:' + key, int(os.getenv('IP_CHECKS_PER_HOUR', '100')))]
    try:
        allowed = db.allow_request(get_settings().sqlite_path, buckets)
    except (sqlite3.Error, OSError):
        now = time.monotonic()
        with _lock:
            for bucket in list(_recent):
                queue = _recent[bucket]
                while queue and queue[0] <= now - 3600:
                    queue.popleft()
                if not queue:
                    del _recent[bucket]
            allowed = len(_recent) < 20000 and all(len(_recent.get(b, ())) < limit for b, limit in buckets)
            if allowed:
                for bucket, _ in buckets:
                    _recent.setdefault(bucket, deque()).append(now)
    if not allowed:
        raise ApiError(429, 'rate_limited', 'Too many checks. Please try again in an hour.')
