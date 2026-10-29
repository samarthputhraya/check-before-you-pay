"""Outermost ASGI middleware: body-size limits (with or without Content-Length), a last-resort 500 that never logs
request content, security headers and cache headers.

It is pure ASGI rather than BaseHTTPMiddleware so that it sees chunked bodies byte by byte and catches every
exception before uvicorn would log a traceback that could contain a user's message.
"""
from __future__ import annotations

import json
import logging

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.config import MAX_BODY_BYTES

log = logging.getLogger("cbyp")

# /api/check carries base64 files; every other endpoint takes a few hundred bytes of JSON. Dodo's webhook carries the
# whole payment or subscription object (customer, cart, refunds, disputes, metadata), so it gets more room.
SMALL_BODY_BYTES = 64 * 1024
_BODY_LIMITS = {"/api/check": MAX_BODY_BYTES, "/api/dodo/webhook": 256 * 1024}


class BodyTooLarge(StarletteHTTPException):
    """An HTTPException, so FastAPI's body parsing re-raises it unchanged and the error handler maps it to 413."""

    def __init__(self, limit: int) -> None:
        msg = "Files can be at most 5 MB." if limit == MAX_BODY_BYTES else "The request body is too large."
        super().__init__(status_code=413, detail=msg)


def _limit_for(path: str) -> int:
    return _BODY_LIMITS.get(path, SMALL_BODY_BYTES)


def _cache_control(path: str) -> bytes | None:
    if path.startswith("/api/") or path.startswith("/c/"):
        return None
    if path.startswith("/vendor/"):
        return b"public, max-age=86400"  # pinned library versions; renamed on upgrade
    return b"no-cache"  # the app's own modules and pages: always revalidate after a deploy


async def _send_json(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                            (b"x-content-type-options", b"nosniff")]})
    await send({"type": "http.response.body", "body": body})


class Guard:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope.get("path", "")
        limit = _limit_for(path)
        headers = dict(scope.get("headers") or [])
        length = headers.get(b"content-length")
        if length is not None:
            if not length.isdigit():
                await _send_json(send, 400, "invalid_request", "Content-Length is not valid.")
                return
            if int(length) > limit:
                await _send_json(send, 413, "input_too_large", BodyTooLarge(limit).detail)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise BodyTooLarge(limit)
            return message

        started = False
        cache = _cache_control(path)

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                hdrs = list(message.get("headers") or [])
                names = {k.lower() for k, _ in hdrs}
                if b"x-content-type-options" not in names:
                    hdrs.append((b"x-content-type-options", b"nosniff"))
                if b"referrer-policy" not in names:
                    hdrs.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                if cache and b"cache-control" not in names:
                    hdrs.append((b"cache-control", cache))
                message = {**message, "headers": hdrs}
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except BodyTooLarge as exc:
            if not started:
                await _send_json(send, 413, "input_too_large", exc.detail)
        except Exception as exc:  # noqa: BLE001 - last resort; never let a traceback with user content reach the logs
            log.error("unhandled %s on %s %s", type(exc).__name__, scope.get("method"), path)
            if not started:
                await _send_json(send, 500, "internal_error", "Something went wrong on our side. Please try again.")
