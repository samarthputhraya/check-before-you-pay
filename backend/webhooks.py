"""viaSocket delivery of masked report metadata; durable retries never delay a check."""
from __future__ import annotations

import asyncio
import os
import sqlite3
from urllib.parse import urlsplit

import httpx

from backend import db
from backend.config import get_settings

_delivery_lock = asyncio.Lock()


async def deliver_pending() -> None:
    url = os.getenv('VIASOCKET_REPORT_WEBHOOK_URL', '').strip()
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        return
    async with _delivery_lock:
        path = get_settings().sqlite_path
        try:
            reports = await asyncio.to_thread(db.pending_webhooks, path)
        except (OSError, sqlite3.Error):
            return
        async with httpx.AsyncClient(timeout=2, follow_redirects=False) as client:
            for report in reports:
                try:
                    view = await asyncio.to_thread(db.get_check, path, report['check_id'])
                    if not view:
                        continue
                    # No source message, consented text, note, recipient, raw entity or anonymous user ID.
                    payload = {'event':'report', 'report_id':report['id'], 'check_id':view.check_id,
                               'band':view.band, 'score':view.score, 'lang':view.lang,
                               'entities':[e.model_dump() for e in view.entities],
                               'url':view.share.url.split('?')[0]}
                    response = await client.post(url, json=payload,
                        headers={'Idempotency-Key':report['id']})
                    response.raise_for_status()
                    delivered = True
                except Exception:
                    delivered = False
                try:
                    await asyncio.to_thread(db.webhook_result, path, report['id'], delivered)
                except (OSError, sqlite3.Error):
                    return


async def worker() -> None:
    while True:
        await deliver_pending()
        await asyncio.sleep(30)
