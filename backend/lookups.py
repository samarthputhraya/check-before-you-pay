"""Bounded RDAP lookup and exact URL feed matching. Never fetch a user-supplied URL."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from backend.config import ROOT
from backend.extraction import canonical_url, registered_domain

_ages: dict[str, tuple[float, tuple[int, str]]] = {}
_feed: tuple[str, float, set[str]] | None = None
UNREGISTERED = -1  # Negative RDAP answer, not an age or a scoring change.


async def domain_age(domain: str) -> tuple[int, str] | None:
    domain = registered_domain(domain)
    cached = _ages.get(domain)
    if cached and time.monotonic() - cached[0] < 3600:
        return cached[1]
    try:
        bootstrap = json.loads((ROOT / 'seed/rdap_bootstrap.json').read_text(encoding='utf-8'))
        tld = domain.rsplit('.', 1)[-1]
        base = next(url for tlds, urls in bootstrap['services'] if tld in tlds for url in urls if url.startswith('https://'))
        url = base.rstrip('/') + '/domain/' + quote(domain, safe='.-')
        async with asyncio.timeout(2):
            async with httpx.AsyncClient(timeout=2, follow_redirects=False) as client:
                async with client.stream('GET', url, headers={'Accept':'application/rdap+json'}) as response:
                    if response.status_code == 404:
                        if len(_ages) > 10000:
                            _ages.clear()
                        value = UNREGISTERED, url
                        _ages[domain] = (time.monotonic(), value)
                        return value
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > 1_000_000:
                            return None
        payload = json.loads(chunks)
        dates = [datetime.fromisoformat(e['eventDate'].replace('Z', '+00:00')) for e in payload.get('events', [])
                 if e.get('eventAction') == 'registration']
        if not dates:
            return None
        age = (datetime.now(timezone.utc) - min(dates)).days
        if age < 0:
            return None
        value = age, url
        if len(_ages) > 10000:
            _ages.clear()
        _ages[domain] = (time.monotonic(), value)
        return value
    except (Exception,):
        return None


async def domain_ages(domains: list[str]) -> tuple[dict[str, tuple[int, str]], bool]:
    # Bound attacker-controlled fanout while making independent lookups concurrent.
    domains = sorted(set(registered_domain(d) for d in domains))
    values = await asyncio.gather(*(domain_age(d) for d in domains[:8]))
    return {d:v for d,v in zip(domains[:8], values) if v is not None}, len(domains) > 8 or any(v is None for v in values)


def phishing_hits(urls: list[str]) -> tuple[list[str], bool]:
    global _feed
    if not urls:
        return [], False
    path = os.getenv('PHISHTANK_FEED_PATH', '').strip()
    if not path:
        return [], False  # This optional integration is disabled, not a failed risk check.
    try:
        file = Path(path)
        modified = file.stat().st_mtime
        if time.time() - modified > 86400 or file.stat().st_size > 100_000_000:
            return [], True
        if not _feed or _feed[:2] != (str(file), modified):
            rows = json.loads(file.read_text(encoding='utf-8'))
            values = {canonical_url(row['url']) for row in rows
                      if row.get('verified') == 'yes' and row.get('online') == 'yes'}
            _feed = (str(file), modified, values - {None})
        return [u for u in urls if canonical_url(u) in _feed[2]], False
    except (OSError, ValueError, KeyError, TypeError):
        return [], True
