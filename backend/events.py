"""Server-issued proof for browser share events; anonymous visit counts remain estimates."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from fastapi import Request, Response

COOKIE = 'cbyp_events'
_fallback_key = secrets.token_bytes(32)


def _key() -> bytes:
    salt = os.getenv('IDENTIFIER_SALT', '').encode()
    return salt if len(salt) >= 32 else _fallback_key


def issue(response: Response, anon_id: str, secure: bool) -> None:
    payload = f'{anon_id}|{int(time.time()) + 86400}'
    signature = hmac.new(_key(), ('events:' + payload).encode(), hashlib.sha256).hexdigest()
    response.set_cookie(COOKIE, payload + '|' + signature, max_age=86400,
                        httponly=True, secure=secure, samesite='lax')


def verified(request: Request, anon_id: str) -> bool:
    raw = request.cookies.get(COOKIE, '')
    try:
        owner, expires, signature = raw.split('|')
        payload = owner + '|' + expires
        expected = hmac.new(_key(), ('events:' + payload).encode(), hashlib.sha256).hexdigest()
        return owner == anon_id and int(expires) > time.time() and hmac.compare_digest(expected, signature)
    except (ValueError, TypeError):
        return False
