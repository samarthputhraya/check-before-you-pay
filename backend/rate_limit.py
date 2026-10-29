"""Persistent per-user and per-IP limits, with bounded local protection during a DB outage."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import secrets
import sqlite3
import time
from collections import deque
from threading import Lock

from starlette.requests import Request

from backend import db
from backend.config import get_settings
from backend.errors import ApiError

_lock = Lock()
_recent: dict[str, deque[float]] = {}
_emergency_salt = secrets.token_bytes(32)


def client_ip(request: Request) -> str:
    """Trust Railway's overwritten header only in an explicitly edge-only deployment.

    Uvicorn proxy rewriting is disabled. Local/direct requests always use the
    socket peer; arbitrary X-Forwarded-For values are never used.
    """
    if os.getenv('TRUST_RAILWAY_EDGE') == 'true' and os.getenv('RAILWAY_ENVIRONMENT_ID'):
        values = request.headers.getlist('x-real-ip')
        if len(values) == 1:
            try:
                return str(ipaddress.ip_address(values[0]))
            except ValueError:
                pass
    return request.client.host if request.client else 'unknown'


def _ip_key(ip: str) -> str:
    salt = os.getenv('IDENTIFIER_SALT', '').encode() or _emergency_salt
    return hmac.new(salt, ip.encode(), hashlib.sha256).hexdigest()


def enforce(anon_id: str, ip: str) -> None:
    # Per-user limits stay strict; the coarse IP budget allows a shared house Wi-Fi.
    _enforce_buckets([('user:' + anon_id, 30),
                      ('ip:' + _ip_key(ip), int(os.getenv('IP_CHECKS_PER_HOUR', '3000')))])


def enforce_events(anon_id: str, ip: str) -> None:
    _enforce_buckets([('events:user:' + anon_id, 300), ('events:ip:' + _ip_key(ip), 10000)])


def enforce_quiz(anon_id: str, ip: str) -> None:
    # Each answer writes a quiz_results row, which unlocks quiz_shared; cap it so plays can't be farmed.
    _enforce_buckets([('quiz:user:' + anon_id, 30),
                      ('quiz:ip:' + _ip_key(ip), int(os.getenv('IP_QUIZ_PER_HOUR', '3000')))],
                     'Too many quiz answers. Please try again in an hour.')


def _enforce_buckets(buckets: list[tuple[str, int]],
                     message: str = 'Too many checks. Please try again in an hour.') -> None:
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
        raise ApiError(429, 'rate_limited', message)
